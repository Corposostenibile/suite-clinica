import { useState, useEffect, useCallback } from 'react';
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
import { FaUserCircle, FaIdCard, FaLayerGroup, FaSave, FaAppleAlt, FaClipboardCheck, FaBrain, FaRunning, FaCheck } from 'react-icons/fa';

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

  // State
  const [cliente, setCliente] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [activeTab, setActiveTab] = useState('anagrafica');



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
        target: '[data-tour="nutrizione-piani"]',
        title: 'Piani Alimentari',
        content: 'Il cuore della nutrizione: carica nuovi PDF, modifica quelli attivi e consulta lo storico.',
        placement: 'top',
        icon: <FaAppleAlt size={18} color="white" />,
        iconBg: 'linear-gradient(135deg, #10B981, #34D399)',
        tabId: 'nutrizione',
        onEnter: () => setNutrizioneSubTab('piano')
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
    const validTabs = new Set([
      'anagrafica', 'programma', 'team', 'nutrizione', 'coaching', 'psicologia', 'check_periodici', 'check_iniziali'
    ]);

    if (validTabs.has(mapped)) {
      setActiveTab(mapped);
    }
  }, [searchParams]);

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
  // Anamnesi state
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
  // Psicologia Anamnesi (storia psicologica) - già in formData
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
    data_scadenza_nutrizione: '',
    data_inizio_coach: '',
    data_scadenza_coach: '',
    data_inizio_psicologia: '',
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
    patologia_diabete: false,
    patologia_ipertensione: false,
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
    patologia_psico_altro_check: false,
    patologia_psico_altro: '',
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
      if (nutrizioneSubTab === 'anamnesi') {
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
      } else if (psicologiaSubTab === 'diario') {
        fetchDiarioPsicologia();
      }
    }
  }, [activeTab, psicologiaSubTab, id]);

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
      const result = await checkService.getResponseDetail(response.type, response.id);
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
      await clientiService.declineCallBonus(callBonusResponseModal.id);
      setCallBonusResponseModal(null);
      fetchCallBonusHistory();
    } catch (err) {
      console.error('Error declining call bonus:', err);
      alert('Errore nel rifiuto. Riprova.');
    } finally {
      setDecliningCallBonus(false);
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
        setAnamnesiContent(response.anamnesi.content || '');
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
      const [nutri, coach, psico, hm] = await Promise.all([
        teamService.getAvailableProfessionals('nutrizione'),
        teamService.getAvailableProfessionals('coach'),
        teamService.getAvailableProfessionals('psicologia'),
        teamService.getAvailableProfessionals('health_manager'),
      ]);
      setAvailableProfessionals({
        nutrizionista: nutri.professionals || [],
        coach: coach.professionals || [],
        psicologa: psico.professionals || [],
        health_manager: hm.professionals || [],
      });
    } catch (err) {
      console.error('Error fetching available professionals:', err);
    }
  };

  // Handle assign professional
  const handleOpenAssignModal = (tipo) => {
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
      durata_programma_giorni: c.durata_programma_giorni || c.durataProgrammaGiorni || '',
      data_rinnovo: c.data_rinnovo || c.dataRinnovo || '',
      data_inizio_nutrizione: c.data_inizio_nutrizione || c.dataInizioNutrizione || '',
      data_scadenza_nutrizione: c.data_scadenza_nutrizione || c.dataScadenzaNutrizione || '',
      data_inizio_coach: c.data_inizio_coach || c.dataInizioCoach || '',
      data_scadenza_coach: c.data_scadenza_coach || c.dataScadenzaCoach || '',
      data_inizio_psicologia: c.data_inizio_psicologia || c.dataInizioPsicologia || '',
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
      patologia_psico_altro_check: c.patologia_psico_altro_check || c.patologiaPsicoAltroCheck || (!!c.patologia_psico_altro) || false,
      patologia_psico_altro: c.patologia_psico_altro || c.patologiaPsicoAltro || '',
    });

    // Check custom professione
    const allProfessioni = PROFESSIONI_OPTIONS.flatMap(g => g.options);
    if (c.professione && !allProfessioni.includes(c.professione)) {
      setShowProfessioneAltro(true);
      setProfessioneAltro(c.professione);
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

  // Loading state
  if (loading) {
    return (
      <div className="d-flex justify-content-center align-items-center py-5">
        <div className="spinner-border text-primary" role="status">
          <span className="visually-hidden">Caricamento...</span>
        </div>
      </div>
    );
  }

  // Error state
  if (error && !cliente) {
    return (
      <div className="alert alert-danger d-flex align-items-center">
        <i className="ri-error-warning-line me-2 fs-4"></i>
        <div className="flex-grow-1">{error}</div>
        <Link to="/clienti-lista" className="btn btn-sm btn-outline-danger">
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

  // Tabs configuration
  const mainTabs = [
    { id: 'anagrafica', label: 'Anagrafica', icon: 'ri-user-line' },
    { id: 'programma', label: 'Programma', icon: 'ri-file-list-3-line' },
    { id: 'team', label: 'Team', icon: 'ri-team-line' },
    { id: 'nutrizione', label: 'Nutrizione', icon: 'ri-heart-pulse-line' },
    { id: 'coaching', label: 'Coaching', icon: 'ri-run-line' },
    { id: 'psicologia', label: 'Psicologia', icon: 'ri-mental-health-line' },
    { id: 'check_periodici', label: 'Check Periodici', icon: 'ri-calendar-check-line' },
    { id: 'check_iniziali', label: 'Check Iniziali', icon: 'ri-file-list-2-line' },
    { id: 'tickets', label: 'Ticket', icon: 'ri-ticket-2-line' },
    { id: 'call_bonus', label: 'Call Bonus', icon: 'ri-phone-line' },
  ];

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
      <div className="d-flex flex-wrap align-items-center justify-content-between gap-3 mb-4" data-tour="header-dettaglio">
        <div>
          <h4 className="mb-1">Dettaglio Paziente</h4>
          <nav aria-label="breadcrumb">
            <ol className="breadcrumb mb-0">
              <li className="breadcrumb-item">
                <Link to="/clienti-lista">Pazienti</Link>
              </li>
              <li className="breadcrumb-item active">{c.nome}</li>
            </ol>
          </nav>
        </div>
        <div className="d-flex gap-2">
          <Link to="/clienti-lista" className="btn btn-outline-secondary">
            <i className="ri-arrow-left-line me-1"></i>
            Torna alla Lista
          </Link>
          <button className="btn btn-primary" onClick={handleSave} disabled={saving} data-tour="salva-modifiche">
            {saving ? (
              <><span className="spinner-border spinner-border-sm me-2"></span>Salvataggio...</>
            ) : saveSuccess ? (
              <><i className="ri-check-line me-1"></i>Salvato!</>
            ) : (
              <><i className="ri-save-line me-1"></i>Salva Modifiche</>
            )}
          </button>
        </div>
      </div>

      {/* Success/Error alerts */}
      {saveSuccess && (
        <div className="alert alert-success alert-dismissible fade show mb-4">
          <i className="ri-check-double-line me-2"></i>
          Modifiche salvate con successo!
        </div>
      )}
      {error && (
        <div className="alert alert-danger alert-dismissible fade show mb-4">
          <i className="ri-error-warning-line me-2"></i>
          {error}
          <button type="button" className="btn-close" onClick={() => setError(null)}></button>
        </div>
      )}

      <div className="row g-4">
        {/* Profile Card - Left Column */}
        <div className="col-lg-4" data-tour="profilo-paziente">
          <div className="card shadow-sm border-0 overflow-hidden">
            {/* Gradient Header */}
            <div
              className="position-relative"
              style={{ background: statusGradient, height: '120px' }}
            >
              {/* Status badges */}
              <div className="position-absolute top-0 start-0 p-3 d-flex gap-2">
                <span className={`badge bg-${statusColor}`}>
                  <i className={`ri-${c.statoCliente === 'attivo' ? 'checkbox-circle' : 'close-circle'}-line me-1`}></i>
                  {STATO_LABELS[c.statoCliente] || c.statoCliente}
                </span>
                {c.alert && (
                  <span className="badge bg-danger">
                    <i className="ri-alarm-warning-line me-1"></i>Alert
                  </span>
                )}
              </div>

              {/* Avatar */}
              <div className="position-absolute start-50 translate-middle-x" style={{ bottom: '-50px' }}>
                <div
                  className="rounded-circle border border-4 border-white shadow d-flex align-items-center justify-content-center"
                  style={{ width: '100px', height: '100px', background: '#fff' }}
                >
                  <span className="fw-bold text-primary" style={{ fontSize: '2rem' }}>
                    {getInitials(c.nome)}
                  </span>
                </div>
              </div>
            </div>

            {/* Card Body */}
            <div className="card-body text-center pt-5 mt-3">
              <h4 className="mb-1">{c.nome}</h4>
              <p className="text-muted mb-3">
                {formData.mail || 'Nessuna email'}
              </p>

              {/* Badges */}
              <div className="d-flex justify-content-center gap-2 flex-wrap mb-4">
                {c.tipologia && (
                  <span className="badge bg-info-subtle text-info">
                    {TIPOLOGIA_LABELS[c.tipologia] || c.tipologia}
                  </span>
                )}
                {c.programma && (
                  <span className="badge bg-primary-subtle text-primary">
                    {c.programma}
                  </span>
                )}
              </div>

              {/* Quick Stats */}
              <div className="row g-3 mb-4">
                <div className="col-6">
                  <div className="bg-light rounded-3 p-3">
                    <div className="text-muted small mb-1">ID Paziente</div>
                    <div className="fw-semibold">#{c.id}</div>
                  </div>
                </div>
                <div className="col-6">
                  <div className="bg-light rounded-3 p-3">
                    <div className="text-muted small mb-1">Età</div>
                    <div className="fw-semibold">{age ? `${age} anni` : '-'}</div>
                  </div>
                </div>
                <div className="col-6">
                  <div className="bg-light rounded-3 p-3">
                    <div className="text-muted small mb-1">Giorni Rimanenti</div>
                    <div className="fw-semibold">{c.giorniRimanenti || '-'}</div>
                  </div>
                </div>
                <div className="col-6">
                  <div className="bg-light rounded-3 p-3">
                    <div className="text-muted small mb-1">Rinnovo</div>
                    <div className="fw-semibold">
                      {c.dataRinnovo ? new Date(c.dataRinnovo).toLocaleDateString('it-IT') : '-'}
                    </div>
                  </div>
                </div>
              </div>

              {/* Team Quick View */}
              <h6 className="text-uppercase text-muted small fw-semibold mb-3">Team Assegnato</h6>
              <div className="mb-4">
                {/* Nutrizionisti */}
                {c.nutrizionistiMultipli?.length > 0 && (
                  <div className="mb-3">
                    <div className="d-flex align-items-center gap-2 mb-2">
                      <div className="bg-success rounded-circle d-flex align-items-center justify-content-center"
                           style={{ width: '20px', height: '20px' }}>
                        <i className="ri-heart-pulse-line text-white" style={{ fontSize: '0.65rem' }}></i>
                      </div>
                      <small className="text-muted fw-semibold">Nutrizione</small>
                    </div>
                    {c.nutrizionistiMultipli.map((prof, idx) => (
                      <div key={idx} className="d-flex align-items-center gap-2 ms-4 mb-1">
                        {prof.avatar_path ? (
                          <img
                            src={prof.avatar_path}
                            alt=""
                            className="rounded-circle"
                            style={{ width: '28px', height: '28px', objectFit: 'cover' }}
                          />
                        ) : (
                          <div
                            className="rounded-circle bg-success text-white d-flex align-items-center justify-content-center"
                            style={{ width: '28px', height: '28px', fontSize: '0.7rem' }}
                          >
                            {(prof.full_name || prof.email || '??').split(' ').map(n => n[0]).join('').substring(0, 2).toUpperCase()}
                          </div>
                        )}
                        <small className="fw-medium">{prof.full_name || prof.email}</small>
                      </div>
                    ))}
                  </div>
                )}

                {/* Coach */}
                {c.coachesMultipli?.length > 0 && (
                  <div className="mb-3">
                    <div className="d-flex align-items-center gap-2 mb-2">
                      <div className="bg-warning rounded-circle d-flex align-items-center justify-content-center"
                           style={{ width: '20px', height: '20px' }}>
                        <i className="ri-run-line text-dark" style={{ fontSize: '0.65rem' }}></i>
                      </div>
                      <small className="text-muted fw-semibold">Coach</small>
                    </div>
                    {c.coachesMultipli.map((prof, idx) => (
                      <div key={idx} className="d-flex align-items-center gap-2 ms-4 mb-1">
                        {prof.avatar_path ? (
                          <img
                            src={prof.avatar_path}
                            alt=""
                            className="rounded-circle"
                            style={{ width: '28px', height: '28px', objectFit: 'cover' }}
                          />
                        ) : (
                          <div
                            className="rounded-circle bg-warning text-dark d-flex align-items-center justify-content-center"
                            style={{ width: '28px', height: '28px', fontSize: '0.7rem' }}
                          >
                            {(prof.full_name || prof.email || '??').split(' ').map(n => n[0]).join('').substring(0, 2).toUpperCase()}
                          </div>
                        )}
                        <small className="fw-medium">{prof.full_name || prof.email}</small>
                      </div>
                    ))}
                  </div>
                )}

                {/* Psicologi */}
                {c.psicologiMultipli?.length > 0 && (
                  <div className="mb-3">
                    <div className="d-flex align-items-center gap-2 mb-2">
                      <div className="bg-info rounded-circle d-flex align-items-center justify-content-center"
                           style={{ width: '20px', height: '20px' }}>
                        <i className="ri-mental-health-line text-white" style={{ fontSize: '0.65rem' }}></i>
                      </div>
                      <small className="text-muted fw-semibold">Psicologia</small>
                    </div>
                    {c.psicologiMultipli.map((prof, idx) => (
                      <div key={idx} className="d-flex align-items-center gap-2 ms-4 mb-1">
                        {prof.avatar_path ? (
                          <img
                            src={prof.avatar_path}
                            alt=""
                            className="rounded-circle"
                            style={{ width: '28px', height: '28px', objectFit: 'cover' }}
                          />
                        ) : (
                          <div
                            className="rounded-circle bg-info text-white d-flex align-items-center justify-content-center"
                            style={{ width: '28px', height: '28px', fontSize: '0.7rem' }}
                          >
                            {(prof.full_name || prof.email || '??').split(' ').map(n => n[0]).join('').substring(0, 2).toUpperCase()}
                          </div>
                        )}
                        <small className="fw-medium">{prof.full_name || prof.email}</small>
                      </div>
                    ))}
                  </div>
                )}

                {/* Nessun professionista */}
                {!c.nutrizionistiMultipli?.length && !c.coachesMultipli?.length && !c.psicologiMultipli?.length && (
                  <div className="text-center py-2">
                    <small className="text-muted">Nessun professionista assegnato</small>
                  </div>
                )}
              </div>

              {/* Action Buttons */}
              <div className="d-grid gap-2">
                <button
                  className="btn btn-outline-danger"
                  onClick={() => setShowDeleteModal(true)}
                >
                  <i className="ri-delete-bin-line me-2"></i>
                  Elimina Paziente
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* Details Section - Right Column */}
        <div className="col-lg-8">
          <div className="card shadow-sm border-0">
            {/* Tabs Navigation */}
            <div className="card-header bg-transparent border-bottom p-0">
              <ul className="nav nav-tabs border-0 flex-nowrap overflow-auto" data-tour="nav-tabs-dettaglio">
                {mainTabs.map(tab => (
                  <li key={tab.id} className="nav-item">
                    <button
                      className={`nav-link px-4 py-3 ${activeTab === tab.id ? 'active' : ''}`}
                      onClick={() => setActiveTab(tab.id)}
                      style={{ whiteSpace: 'nowrap' }}
                    >
                      <i className={`${tab.icon} me-2`}></i>
                      {tab.label}
                    </button>
                  </li>
                ))}
              </ul>
            </div>

            {/* Tab Content */}
            <div className="card-body">
              {/* ========== ANAGRAFICA TAB ========== */}
              {activeTab === 'anagrafica' && (
                <div className="row g-4">
                  {/* Dati Personali */}
                  <div className="col-md-6" data-tour="anagrafica-dati">
                    <h6 className="text-uppercase text-muted small fw-semibold mb-3">
                      Dati Personali
                    </h6>
                    <div className="mb-3">
                      <label className="form-label small text-muted">Nome Completo</label>
                      <input
                        type="text"
                        className="form-control"
                        value={formData.nome_cognome}
                        onChange={(e) => handleInputChange('nome_cognome', e.target.value)}
                      />
                    </div>
                    <div className="mb-3">
                      <label className="form-label small text-muted">Data di Nascita</label>
                      <input
                        type="date"
                        className="form-control"
                        value={formData.data_di_nascita}
                        onChange={(e) => handleInputChange('data_di_nascita', e.target.value)}
                      />
                    </div>
                    <div className="mb-3">
                      <label className="form-label small text-muted">Genere</label>
                      <select
                        className="form-select"
                        value={formData.genere}
                        onChange={(e) => handleInputChange('genere', e.target.value)}
                      >
                        <option value="">Seleziona...</option>
                        {Object.entries(GENERE_LABELS).map(([value, label]) => (
                          <option key={value} value={value}>{label}</option>
                        ))}
                      </select>
                    </div>
                    <div className="mb-3">
                      <label className="form-label small text-muted">Professione</label>
                      <select
                        className="form-select"
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
                      <div className="mb-3">
                        <input
                          type="text"
                          className="form-control"
                          placeholder="Specifica professione..."
                          value={professioneAltro}
                          onChange={(e) => setProfessioneAltro(e.target.value)}
                        />
                      </div>
                    )}
                  </div>

                  {/* Contatti */}
                  <div className="col-md-6" data-tour="anagrafica-contatti">
                    <h6 className="text-uppercase text-muted small fw-semibold mb-3">
                      Contatti
                    </h6>
                    <div className="mb-3">
                      <label className="form-label small text-muted">Email</label>
                      <input
                        type="email"
                        className="form-control"
                        value={formData.mail}
                        onChange={(e) => handleInputChange('mail', e.target.value)}
                      />
                    </div>
                    <div className="mb-3">
                      <label className="form-label small text-muted">Telefono</label>
                      <input
                        type="tel"
                        className="form-control"
                        value={formData.numero_telefono}
                        onChange={(e) => handleInputChange('numero_telefono', e.target.value)}
                      />
                    </div>
                    <div className="mb-3">
                      <label className="form-label small text-muted">Indirizzo</label>
                      <input
                        type="text"
                        className="form-control"
                        value={formData.indirizzo}
                        onChange={(e) => handleInputChange('indirizzo', e.target.value)}
                      />
                    </div>
                    <div className="mb-3">
                      <label className="form-label small text-muted">Paese</label>
                      <input
                        type="text"
                        className="form-control"
                        value={formData.paese}
                        onChange={(e) => handleInputChange('paese', e.target.value)}
                      />
                    </div>
                  </div>

                  {/* Storia */}
                  <div className="col-12" data-tour="anagrafica-storia">
                    <h6 className="text-uppercase text-muted small fw-semibold mb-3">
                      Storia e Obiettivi
                    </h6>
                    <div className="mb-3">
                      <label className="form-label small text-muted">Storia del Cliente</label>
                      <textarea
                        className="form-control"
                        rows="3"
                        value={formData.storia_cliente}
                        onChange={(e) => handleInputChange('storia_cliente', e.target.value)}
                      ></textarea>
                    </div>
                    <div className="row g-3">
                      <div className="col-md-4">
                        <label className="form-label small text-muted">Problema</label>
                        <textarea
                          className="form-control"
                          rows="2"
                          value={formData.problema}
                          onChange={(e) => handleInputChange('problema', e.target.value)}
                        ></textarea>
                      </div>
                      <div className="col-md-4">
                        <label className="form-label small text-muted">Paure</label>
                        <textarea
                          className="form-control"
                          rows="2"
                          value={formData.paure}
                          onChange={(e) => handleInputChange('paure', e.target.value)}
                        ></textarea>
                      </div>
                      <div className="col-md-4">
                        <label className="form-label small text-muted">Conseguenze</label>
                        <textarea
                          className="form-control"
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
                <div className="row g-4">
                  {/* Stato */}
                  <div className="col-md-6" data-tour="programma-stato">
                    <h6 className="text-uppercase text-muted small fw-semibold mb-3">
                      Stato Cliente
                    </h6>
                    <div className="mb-3">
                      <label className="form-label small text-muted">Stato</label>
                      <select
                        className="form-select"
                        value={formData.stato_cliente}
                        onChange={(e) => handleInputChange('stato_cliente', e.target.value)}
                      >
                        <option value="">Seleziona...</option>
                        {Object.entries(STATO_LABELS).map(([value, label]) => (
                          <option key={value} value={value}>{label}</option>
                        ))}
                      </select>
                    </div>
                    <div className="mb-3">
                      <label className="form-label small text-muted">Tipologia</label>
                      <select
                        className="form-select"
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
                  <div className="col-md-6">
                    <h6 className="text-uppercase text-muted small fw-semibold mb-3">
                      Programma
                    </h6>
                    <div className="mb-3">
                      <label className="form-label small text-muted">Programma Attuale</label>
                      <input
                        type="text"
                        className="form-control"
                        value={formData.programma_attuale}
                        onChange={(e) => handleInputChange('programma_attuale', e.target.value)}
                      />
                    </div>
                    <div className="mb-3">
                      <label className="form-label small text-muted">Durata (giorni)</label>
                      <input
                        type="number"
                        className="form-control"
                        value={formData.durata_programma_giorni}
                        onChange={(e) => handleInputChange('durata_programma_giorni', e.target.value)}
                      />
                    </div>
                  </div>

                  {/* Date abbonamento generali (legacy / riepilogo) */}
                  <div className="col-12" data-tour="programma-date">
                    <h6 className="text-uppercase text-muted small fw-semibold mb-3">
                      Date Abbonamento (generale)
                    </h6>
                    <div className="row g-3">
                      <div className="col-md-6">
                        <label className="form-label small text-muted">Data Inizio</label>
                        <input
                          type="date"
                          className="form-control"
                          value={formData.data_inizio_abbonamento}
                          onChange={(e) => handleInputChange('data_inizio_abbonamento', e.target.value)}
                        />
                      </div>
                      <div className="col-md-6">
                        <label className="form-label small text-muted">Data Scadenza</label>
                        <input
                          type="date"
                          className="form-control"
                          value={formData.data_rinnovo}
                          onChange={(e) => handleInputChange('data_rinnovo', e.target.value)}
                        />
                      </div>
                    </div>
                  </div>

                  {/* Date per piano (Nutrizione, Coach, Psicologia) */}
                  <div className="col-12" data-tour="programma-date-per-piano">
                    <h6 className="text-uppercase text-muted small fw-semibold mb-3">
                      Date per piano
                    </h6>
                    <div className="row g-3">
                      {/* Nutrizione */}
                      <div className="col-12">
                        <div className="card border-0 bg-light rounded-3 p-3">
                          <div className="small fw-semibold text-muted mb-2">
                            <i className="ri-heart-pulse-line me-1"></i> Nutrizione
                          </div>
                          <div className="row g-2">
                            <div className="col-md-6">
                              <label className="form-label small text-muted mb-0">Data Inizio</label>
                              <input
                                type="date"
                                className="form-control form-control-sm"
                                value={formData.data_inizio_nutrizione || ''}
                                onChange={(e) => handleInputChange('data_inizio_nutrizione', e.target.value)}
                              />
                            </div>
                            <div className="col-md-6">
                              <label className="form-label small text-muted mb-0">Data Scadenza</label>
                              <input
                                type="date"
                                className="form-control form-control-sm"
                                value={formData.data_scadenza_nutrizione || ''}
                                onChange={(e) => handleInputChange('data_scadenza_nutrizione', e.target.value)}
                              />
                            </div>
                          </div>
                        </div>
                      </div>
                      {/* Coach */}
                      <div className="col-12">
                        <div className="card border-0 bg-light rounded-3 p-3">
                          <div className="small fw-semibold text-muted mb-2">
                            <i className="ri-run-line me-1"></i> Coach
                          </div>
                          <div className="row g-2">
                            <div className="col-md-6">
                              <label className="form-label small text-muted mb-0">Data Inizio</label>
                              <input
                                type="date"
                                className="form-control form-control-sm"
                                value={formData.data_inizio_coach || ''}
                                onChange={(e) => handleInputChange('data_inizio_coach', e.target.value)}
                              />
                            </div>
                            <div className="col-md-6">
                              <label className="form-label small text-muted mb-0">Data Scadenza</label>
                              <input
                                type="date"
                                className="form-control form-control-sm"
                                value={formData.data_scadenza_coach || ''}
                                onChange={(e) => handleInputChange('data_scadenza_coach', e.target.value)}
                              />
                            </div>
                          </div>
                        </div>
                      </div>
                      {/* Psicologia */}
                      <div className="col-12">
                        <div className="card border-0 bg-light rounded-3 p-3">
                          <div className="small fw-semibold text-muted mb-2">
                            <i className="ri-mental-health-line me-1"></i> Psicologia
                          </div>
                          <div className="row g-2">
                            <div className="col-md-6">
                              <label className="form-label small text-muted mb-0">Data Inizio</label>
                              <input
                                type="date"
                                className="form-control form-control-sm"
                                value={formData.data_inizio_psicologia || ''}
                                onChange={(e) => handleInputChange('data_inizio_psicologia', e.target.value)}
                              />
                            </div>
                            <div className="col-md-6">
                              <label className="form-label small text-muted mb-0">Data Scadenza</label>
                              <input
                                type="date"
                                className="form-control form-control-sm"
                                value={formData.data_scadenza_psicologia || ''}
                                onChange={(e) => handleInputChange('data_scadenza_psicologia', e.target.value)}
                              />
                            </div>
                          </div>
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
                    <ul className="nav nav-pills mb-4" style={{ gap: '8px' }}>
                      <li className="nav-item">
                        <button
                          className={`nav-link ${teamSubTab === 'clinico' ? 'active' : ''}`}
                          onClick={() => setTeamSubTab('clinico')}
                          style={{
                            background: teamSubTab === 'clinico' ? 'linear-gradient(135deg, #22c55e 0%, #16a34a 100%)' : '#f1f5f9',
                            color: teamSubTab === 'clinico' ? '#fff' : '#64748b',
                            border: 'none',
                            borderRadius: '8px',
                            padding: '10px 20px',
                            fontWeight: 600,
                          }}
                        >
                          <i className="ri-heart-pulse-line me-2"></i>
                          Team Clinico
                        </button>
                      </li>
                      <li className="nav-item">
                        <button
                          className={`nav-link ${teamSubTab === 'esterno' ? 'active' : ''}`}
                          onClick={() => setTeamSubTab('esterno')}
                          style={{
                            background: teamSubTab === 'esterno' ? 'linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%)' : '#f1f5f9',
                            color: teamSubTab === 'esterno' ? '#fff' : '#64748b',
                            border: 'none',
                            borderRadius: '8px',
                            padding: '10px 20px',
                            fontWeight: 600,
                          }}
                        >
                          <i className="ri-team-line me-2"></i>
                          Team Esterno
                        </button>
                      </li>
                    </ul>
                  </div>

                  {/* ===== TEAM CLINICO ===== */}
                  {teamSubTab === 'clinico' && (
                    <div className="col-12" data-tour="team-clinico-wrapper">
                      <div className="row g-4">
                      {/* Professionisti Clinici */}
                      <div className="col-12">
                        <h6 className="text-uppercase text-muted small fw-semibold mb-3">
                          Professionisti Assegnati
                        </h6>
                        {loadingHistory ? (
                          <div className="text-center py-4">
                            <div className="spinner-border spinner-border-sm text-primary" role="status"></div>
                            <small className="ms-2 text-muted">Caricamento...</small>
                          </div>
                        ) : (
                          <div className="row g-3 align-items-start">
                            {/* Nutrizionisti */}
                            <div className="col-md-4">
                              <div className="card border">
                                <div className="card-body p-3">
                                  <div className="d-flex align-items-center justify-content-between mb-2">
                                    <div className="d-flex align-items-center">
                                      <div className="bg-success-subtle rounded-circle d-flex align-items-center justify-content-center me-2"
                                           style={{ width: '28px', height: '28px' }}>
                                        <i className="ri-heart-pulse-line text-success" style={{ fontSize: '0.85rem' }}></i>
                                      </div>
                                      <span className="fw-semibold" style={{ fontSize: '0.9rem' }}>Nutrizionista</span>
                                    </div>
                                    <button
                                      className="btn btn-success btn-sm d-flex align-items-center justify-content-center"
                                      onClick={() => handleOpenAssignModal('nutrizionista')}
                                      title="Aggiungi Nutrizionista"
                                      style={{ width: '26px', height: '26px', padding: 0 }}
                                    >
                                      <i className="ri-add-line" style={{ fontSize: '0.9rem' }}></i>
                                    </button>
                                  </div>
                                  {getActiveProfessionals('nutrizionista').length > 0 ? (
                                    getActiveProfessionals('nutrizionista').map((assignment, idx) => (
                                      <div key={idx} className="d-flex align-items-center justify-content-between mb-2 p-2 bg-light rounded">
                                        <div className="d-flex align-items-center">
                                          {assignment.avatar_path ? (
                                            <img
                                              src={assignment.avatar_path}
                                              alt=""
                                              className="rounded-circle me-2"
                                              style={{ width: '28px', height: '28px', objectFit: 'cover' }}
                                            />
                                          ) : (
                                            <div className="rounded-circle bg-success text-white d-flex align-items-center justify-content-center me-2"
                                                 style={{ width: '28px', height: '28px', fontSize: '0.7rem' }}>
                                              {assignment.professionista_nome?.split(' ').map(n => n[0]).join('').substring(0,2).toUpperCase() || '??'}
                                            </div>
                                          )}
                                          <div>
                                            <small className="d-block fw-medium">{assignment.professionista_nome}</small>
                                            <small className="text-muted" style={{ fontSize: '0.7rem' }}>dal {assignment.data_dal}</small>
                                          </div>
                                        </div>
                                        <button
                                          className="btn btn-sm btn-link text-danger p-0"
                                          onClick={() => handleOpenInterruptModal(assignment)}
                                          title="Rimuovi"
                                        >
                                          <i className="ri-close-line"></i>
                                        </button>
                                      </div>
                                    ))
                                  ) : (
                                    <small className="text-muted">Nessuno assegnato</small>
                                  )}
                                </div>
                              </div>
                            </div>

                            {/* Coach */}
                            <div className="col-md-4">
                              <div className="card border">
                                <div className="card-body p-3">
                                  <div className="d-flex align-items-center justify-content-between mb-2">
                                    <div className="d-flex align-items-center">
                                      <div className="bg-warning-subtle rounded-circle d-flex align-items-center justify-content-center me-2"
                                           style={{ width: '28px', height: '28px' }}>
                                        <i className="ri-run-line text-warning" style={{ fontSize: '0.85rem' }}></i>
                                      </div>
                                      <span className="fw-semibold" style={{ fontSize: '0.9rem' }}>Coach</span>
                                    </div>
                                    <button
                                      className="btn btn-warning btn-sm d-flex align-items-center justify-content-center"
                                      onClick={() => handleOpenAssignModal('coach')}
                                      title="Aggiungi Coach"
                                      style={{ width: '26px', height: '26px', padding: 0 }}
                                    >
                                      <i className="ri-add-line" style={{ fontSize: '0.9rem' }}></i>
                                    </button>
                                  </div>
                                  {getActiveProfessionals('coach').length > 0 ? (
                                    getActiveProfessionals('coach').map((assignment, idx) => (
                                      <div key={idx} className="d-flex align-items-center justify-content-between mb-2 p-2 bg-light rounded">
                                        <div className="d-flex align-items-center">
                                          {assignment.avatar_path ? (
                                            <img
                                              src={assignment.avatar_path}
                                              alt=""
                                              className="rounded-circle me-2"
                                              style={{ width: '28px', height: '28px', objectFit: 'cover' }}
                                            />
                                          ) : (
                                            <div className="rounded-circle bg-warning text-dark d-flex align-items-center justify-content-center me-2"
                                                 style={{ width: '28px', height: '28px', fontSize: '0.7rem' }}>
                                              {assignment.professionista_nome?.split(' ').map(n => n[0]).join('').substring(0,2).toUpperCase() || '??'}
                                            </div>
                                          )}
                                          <div>
                                            <small className="d-block fw-medium">{assignment.professionista_nome}</small>
                                            <small className="text-muted" style={{ fontSize: '0.7rem' }}>dal {assignment.data_dal}</small>
                                          </div>
                                        </div>
                                        <button
                                          className="btn btn-sm btn-link text-danger p-0"
                                          onClick={() => handleOpenInterruptModal(assignment)}
                                          title="Rimuovi"
                                        >
                                          <i className="ri-close-line"></i>
                                        </button>
                                      </div>
                                    ))
                                  ) : (
                                    <small className="text-muted">Nessuno assegnato</small>
                                  )}
                                </div>
                              </div>
                            </div>

                            {/* Psicologi */}
                            <div className="col-md-4">
                              <div className="card border">
                                <div className="card-body p-3">
                                  <div className="d-flex align-items-center justify-content-between mb-2">
                                    <div className="d-flex align-items-center">
                                      <div className="bg-info-subtle rounded-circle d-flex align-items-center justify-content-center me-2"
                                           style={{ width: '28px', height: '28px' }}>
                                        <i className="ri-mental-health-line text-info" style={{ fontSize: '0.85rem' }}></i>
                                      </div>
                                      <span className="fw-semibold" style={{ fontSize: '0.9rem' }}>Psicologo</span>
                                    </div>
                                    <button
                                      className="btn btn-info btn-sm d-flex align-items-center justify-content-center"
                                      onClick={() => handleOpenAssignModal('psicologa')}
                                      title="Aggiungi Psicologo"
                                      style={{ width: '26px', height: '26px', padding: 0 }}
                                    >
                                      <i className="ri-add-line text-white" style={{ fontSize: '0.9rem' }}></i>
                                    </button>
                                  </div>
                                  {getActiveProfessionals('psicologa').length > 0 ? (
                                    getActiveProfessionals('psicologa').map((assignment, idx) => (
                                      <div key={idx} className="d-flex align-items-center justify-content-between mb-2 p-2 bg-light rounded">
                                        <div className="d-flex align-items-center">
                                          {assignment.avatar_path ? (
                                            <img
                                              src={assignment.avatar_path}
                                              alt=""
                                              className="rounded-circle me-2"
                                              style={{ width: '28px', height: '28px', objectFit: 'cover' }}
                                            />
                                          ) : (
                                            <div className="rounded-circle bg-info text-white d-flex align-items-center justify-content-center me-2"
                                                 style={{ width: '28px', height: '28px', fontSize: '0.7rem' }}>
                                              {assignment.professionista_nome?.split(' ').map(n => n[0]).join('').substring(0,2).toUpperCase() || '??'}
                                            </div>
                                          )}
                                          <div>
                                            <small className="d-block fw-medium">{assignment.professionista_nome}</small>
                                            <small className="text-muted" style={{ fontSize: '0.7rem' }}>dal {assignment.data_dal}</small>
                                          </div>
                                        </div>
                                        <button
                                          className="btn btn-sm btn-link text-danger p-0"
                                          onClick={() => handleOpenInterruptModal(assignment)}
                                          title="Rimuovi"
                                        >
                                          <i className="ri-close-line"></i>
                                        </button>
                                      </div>
                                    ))
                                  ) : (
                                    <small className="text-muted">Nessuno assegnato</small>
                                  )}
                                </div>
                              </div>
                            </div>
                          </div>
                        )}
                      </div>

                      {/* Timeline Storico Assegnazioni - Orizzontale */}
                      <div className="col-12 mt-4" data-tour="team-timeline">
                        <h6 className="text-uppercase text-muted small fw-semibold mb-3">
                          <i className="ri-history-line me-2"></i>
                          Storico Assegnazioni
                        </h6>
                        {loadingHistory ? (
                          <div className="text-center py-4">
                            <div className="spinner-border spinner-border-sm text-primary" role="status"></div>
                          </div>
                        ) : getTimelineHistory().length > 0 ? (
                          <div className="timeline-horizontal" style={{
                            overflowX: 'auto',
                            paddingBottom: '10px',
                            position: 'relative',
                          }}>
                            {/* Horizontal line */}
                            <div style={{
                              position: 'absolute',
                              left: '0',
                              right: '0',
                              top: '24px',
                              height: '3px',
                              background: 'linear-gradient(to right, #10b981, #3b82f6, #8b5cf6)',
                              borderRadius: '2px',
                              zIndex: 0,
                            }}></div>

                            <div className="d-flex gap-3 align-items-start" style={{ minWidth: 'max-content', position: 'relative', zIndex: 1 }}>
                              {getTimelineHistory().map((item, idx) => {
                                const colorConfig = TIPO_PROFESSIONISTA_COLORS[item.tipo_professionista] || { bg: 'secondary', icon: 'text-secondary' };
                                const icon = TIPO_PROFESSIONISTA_ICONS[item.tipo_professionista] || 'ri-user-line';

                                return (
                                  <div key={idx} className="timeline-item-h text-center" style={{ minWidth: '160px', maxWidth: '180px' }}>
                                    {/* Dot on line */}
                                    <div className="d-flex justify-content-center mb-2">
                                      <div
                                        className={`rounded-circle d-flex align-items-center justify-content-center bg-${colorConfig.bg}`}
                                        style={{
                                          width: '28px',
                                          height: '28px',
                                          border: '3px solid #fff',
                                          boxShadow: '0 2px 8px rgba(0,0,0,0.15)',
                                        }}
                                      >
                                        <i className={`${icon} text-white`} style={{ fontSize: '0.75rem' }}></i>
                                      </div>
                                    </div>

                                    {/* Date label */}
                                    <div className="small text-muted mb-2" style={{ fontSize: '0.7rem' }}>
                                      {item.data_dal || '—'}
                                      {item.data_al && <span className="d-block">→ {item.data_al}</span>}
                                    </div>

                                    {/* Card */}
                                    <div
                                      className={`card border-0 shadow-sm ${!item.is_active ? 'opacity-75' : ''}`}
                                      style={{
                                        borderRadius: '12px',
                                        background: item.is_active ? '#fff' : '#f8fafc',
                                      }}
                                    >
                                      <div className="card-body p-2">
                                        {/* Status badge */}
                                        <div className="mb-2">
                                          {item.is_active ? (
                                            <span className="badge bg-success" style={{ fontSize: '0.65rem' }}>Attivo</span>
                                          ) : (
                                            <span className="badge bg-secondary" style={{ fontSize: '0.65rem' }}>Concluso</span>
                                          )}
                                        </div>

                                        {/* Avatar */}
                                        <div className="d-flex justify-content-center mb-2">
                                          {item.avatar_path ? (
                                            <img
                                              src={item.avatar_path}
                                              alt=""
                                              className="rounded-circle"
                                              style={{ width: '36px', height: '36px', objectFit: 'cover' }}
                                            />
                                          ) : (
                                            <div
                                              className={`rounded-circle bg-${colorConfig.bg} text-white d-flex align-items-center justify-content-center`}
                                              style={{ width: '36px', height: '36px', fontSize: '0.75rem' }}
                                            >
                                              {item.professionista_nome?.split(' ').map(n => n[0]).join('').substring(0,2).toUpperCase() || '??'}
                                            </div>
                                          )}
                                        </div>

                                        {/* Name */}
                                        <div className="fw-semibold small mb-1" style={{
                                          fontSize: '0.8rem',
                                          whiteSpace: 'nowrap',
                                          overflow: 'hidden',
                                          textOverflow: 'ellipsis',
                                        }}>
                                          {item.professionista_nome}
                                        </div>

                                        {/* Type badge */}
                                        <span className={`badge bg-${colorConfig.bg}-subtle text-${colorConfig.bg}`} style={{ fontSize: '0.6rem' }}>
                                          {TIPO_PROFESSIONISTA_LABELS[item.tipo_professionista] || item.tipo_professionista}
                                        </span>

                                        {/* Motivazione (tooltip style) */}
                                        {item.motivazione_aggiunta && (
                                          <div className="mt-2 text-start" style={{ fontSize: '0.65rem' }}>
                                            <span className="text-success">
                                              <i className="ri-add-line me-1"></i>
                                              {item.motivazione_aggiunta.length > 30
                                                ? item.motivazione_aggiunta.substring(0, 30) + '...'
                                                : item.motivazione_aggiunta}
                                            </span>
                                          </div>
                                        )}
                                        {item.motivazione_interruzione && (
                                          <div className="mt-1 text-start" style={{ fontSize: '0.65rem' }}>
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
                                            <span className="badge bg-warning-subtle text-warning" style={{ fontSize: '0.55rem' }}>
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
                          <div className="text-center py-4 bg-light rounded">
                            <i className="ri-history-line text-muted fs-3 mb-2 d-block"></i>
                            <small className="text-muted">Nessuna assegnazione registrata</small>
                          </div>
                        )}
                      </div>
                      </div>
                    </div>
                  )}

                  {/* ===== TEAM ESTERNO ===== */}
                  {teamSubTab === 'esterno' && (
                    <div className="col-12" data-tour="team-esterno">
                      <div className="card border">
                        <div className="card-body p-3">
                          <div className="d-flex align-items-center justify-content-between mb-2">
                            <div className="d-flex align-items-center">
                              <div className="bg-primary-subtle rounded-circle d-flex align-items-center justify-content-center me-2"
                                   style={{ width: '28px', height: '28px' }}>
                                <i className="ri-user-star-line text-primary" style={{ fontSize: '0.85rem' }}></i>
                              </div>
                              <span className="fw-semibold" style={{ fontSize: '0.9rem' }}>Health Manager</span>
                            </div>
                            <button
                              className="btn btn-primary btn-sm d-flex align-items-center justify-content-center"
                              onClick={() => handleOpenAssignModal('health_manager')}
                              title="Assegna Health Manager"
                              style={{ width: '26px', height: '26px', padding: 0 }}
                            >
                              <i className="ri-add-line" style={{ fontSize: '0.9rem' }}></i>
                            </button>
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
                                <div className="d-flex align-items-center justify-content-between p-2 bg-light rounded">
                                  <div className="d-flex align-items-center">
                                    {hmUser.avatar_path ? (
                                      <img
                                        src={hmUser.avatar_path}
                                        alt=""
                                        className="rounded-circle me-2"
                                        style={{ width: '28px', height: '28px', objectFit: 'cover' }}
                                      />
                                    ) : (
                                      <div className="rounded-circle bg-primary text-white d-flex align-items-center justify-content-center me-2"
                                           style={{ width: '28px', height: '28px', fontSize: '0.7rem' }}>
                                        {(hmUser.full_name || '')
                                          .split(' ')
                                          .map((n) => n[0])
                                          .join('')
                                          .substring(0, 2)
                                          .toUpperCase() || '??'}
                                      </div>
                                    )}
                                    <div>
                                      <small className="d-block fw-medium">{hmUser.full_name || 'Health Manager'}</small>
                                      {hmAssignment?.data_dal && (
                                        <small className="text-muted" style={{ fontSize: '0.7rem' }}>dal {hmAssignment.data_dal}</small>
                                      )}
                                    </div>
                                  </div>
                                  <button
                                    className="btn btn-sm btn-link text-danger p-0"
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
                                </div>
                              );
                            })()
                          ) : (
                            <small className="text-muted">Nessun Health Manager assegnato</small>
                          )}
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* ========== NUTRIZIONE TAB ========== */}
              {activeTab === 'nutrizione' && (
                <div className="row g-4">
                  {/* Alert Criticità - Sempre in evidenza se presente */}
                  {formData.alert_nutrizione && (
                    <div className="col-12">
                      <div className="alert alert-danger border-danger mb-0 d-flex align-items-start">
                        <i className="ri-alarm-warning-line fs-4 me-2 text-danger"></i>
                        <div>
                          <strong className="small">Alert Nutrizione</strong>
                          <p className="mb-0 small">{formData.alert_nutrizione}</p>
                        </div>
                      </div>
                    </div>
                  )}

                  {/* Sub-tab Navigation - Same style as Team tab */}
                  <div className="col-12" data-tour="nutrizione-subtabs">
                    <div style={{ overflowX: 'auto', overflowY: 'hidden', WebkitOverflowScrolling: 'touch', scrollbarWidth: 'none', msOverflowStyle: 'none' }}>
                      <ul className="nav nav-pills mb-0" style={{ gap: '8px', flexWrap: 'nowrap', minWidth: 'max-content' }}>
                        {[
                          { key: 'panoramica', label: 'Panoramica', icon: 'ri-dashboard-line', color: '#22c55e' },
                          { key: 'setup', label: 'Setup', icon: 'ri-settings-3-line', color: '#3b82f6' },
                          { key: 'patologie', label: 'Patologie', icon: 'ri-stethoscope-line', color: '#f59e0b' },
                          { key: 'piano', label: 'Piano Alimentare', icon: 'ri-restaurant-line', color: '#10b981' },
                          { key: 'diario', label: 'Diario', icon: 'ri-book-2-line', color: '#ec4899' },
                          { key: 'alert', label: 'Alert', icon: 'ri-alarm-warning-line', color: '#ef4444' },
                        ].map(({ key, label, icon, color }) => (
                          <li key={key} className="nav-item">
                            <button
                              className="nav-link"
                              onClick={() => setNutrizioneSubTab(key)}
                              style={{
                                background: nutrizioneSubTab === key ? `linear-gradient(135deg, ${color} 0%, ${color}dd 100%)` : '#f1f5f9',
                                color: nutrizioneSubTab === key ? '#fff' : '#64748b',
                                border: 'none',
                                borderRadius: '8px',
                                padding: '8px 16px',
                                fontWeight: 600,
                                fontSize: '0.85rem',
                                whiteSpace: 'nowrap',
                              }}
                            >
                              <i className={`${icon} me-1`}></i>
                              {label}
                            </button>
                          </li>
                        ))}
                      </ul>
                    </div>
                  </div>

                  {/* ===== PANORAMICA SUB-TAB ===== */}
                  {nutrizioneSubTab === 'panoramica' && (
                    <div className="col-12" data-tour="nutrizione-panoramica">
                      <div className="row g-4">
                      {/* Nutrizionisti Assegnati - Same style as Team tab */}
                      <div className="col-12">
                        <h6 className="text-uppercase text-muted small fw-semibold mb-3">
                          Nutrizionisti Assegnati
                        </h6>
                        {loadingHistory ? (
                          <div className="text-center py-4">
                            <div className="spinner-border spinner-border-sm text-success" role="status"></div>
                            <small className="ms-2 text-muted">Caricamento...</small>
                          </div>
                        ) : (
                          <div className="card border">
                            <div className="card-body p-3">
                              <div className="d-flex align-items-center justify-content-between mb-3">
                                <div className="d-flex align-items-center">
                                  <div className="bg-success-subtle rounded-circle d-flex align-items-center justify-content-center me-2"
                                       style={{ width: '32px', height: '32px' }}>
                                    <i className="ri-heart-pulse-line text-success"></i>
                                  </div>
                                  <span className="fw-semibold">Team Nutrizione</span>
                                </div>
                                <span className="badge bg-success">{getActiveProfessionals('nutrizionista').length} attivi</span>
                              </div>

                              {getActiveProfessionals('nutrizionista').length > 0 ? (
                                <div className="d-flex flex-wrap gap-2">
                                  {getActiveProfessionals('nutrizionista').map((assignment, idx) => (
                                    <div key={idx} className="d-flex align-items-center p-2 bg-light rounded">
                                      {assignment.avatar_path ? (
                                        <img src={assignment.avatar_path} alt="" className="rounded-circle me-2" style={{ width: '32px', height: '32px', objectFit: 'cover' }} />
                                      ) : (
                                        <div className="rounded-circle bg-success text-white d-flex align-items-center justify-content-center me-2" style={{ width: '32px', height: '32px', fontSize: '0.75rem' }}>
                                          {assignment.professionista_nome?.split(' ').map(n => n[0]).join('').substring(0,2).toUpperCase() || '??'}
                                        </div>
                                      )}
                                      <div>
                                        <small className="d-block fw-medium">{assignment.professionista_nome}</small>
                                        <small className="text-muted" style={{ fontSize: '0.7rem' }}>dal {assignment.data_dal}</small>
                                      </div>
                                    </div>
                                  ))}
                                </div>
                              ) : (
                                <p className="text-muted small mb-0">Nessun nutrizionista assegnato. Vai alla tab "Team" per assegnare.</p>
                              )}
                            </div>
                          </div>
                        )}
                      </div>

                      {/* Storico Assegnazioni Timeline - Orizzontale come Team tab */}
                      {professionistiHistory.filter(h => h.tipo_professionista === 'nutrizionista').length > 0 && (
                        <div className="col-12">
                          <h6 className="text-uppercase text-muted small fw-semibold mb-3">
                            <i className="ri-history-line me-2"></i>
                            Storico Assegnazioni
                          </h6>
                          <div className="timeline-horizontal" style={{
                            overflowX: 'auto',
                            paddingBottom: '10px',
                            position: 'relative',
                          }}>
                            {/* Horizontal line */}
                            <div style={{
                              position: 'absolute',
                              left: '0',
                              right: '0',
                              top: '24px',
                              height: '3px',
                              background: 'linear-gradient(to right, #22c55e, #16a34a)',
                              borderRadius: '2px',
                              zIndex: 0,
                            }}></div>

                            <div className="d-flex gap-3 align-items-start" style={{ minWidth: 'max-content', position: 'relative', zIndex: 1 }}>
                              {professionistiHistory
                                .filter(h => h.tipo_professionista === 'nutrizionista')
                                .sort((a, b) => {
                                  const dateA = new Date(a.data_dal?.split('/').reverse().join('-') || 0);
                                  const dateB = new Date(b.data_dal?.split('/').reverse().join('-') || 0);
                                  return dateB - dateA;
                                })
                                .map((item, idx) => (
                                  <div key={idx} className="timeline-item-h text-center" style={{ minWidth: '140px', maxWidth: '160px' }}>
                                    {/* Dot on line */}
                                    <div className="d-flex justify-content-center mb-2">
                                      <div
                                        className="rounded-circle d-flex align-items-center justify-content-center bg-success"
                                        style={{
                                          width: '28px',
                                          height: '28px',
                                          border: '3px solid #fff',
                                          boxShadow: '0 2px 8px rgba(0,0,0,0.15)',
                                        }}
                                      >
                                        <i className="ri-heart-pulse-line text-white" style={{ fontSize: '0.75rem' }}></i>
                                      </div>
                                    </div>

                                    {/* Date label */}
                                    <div className="small text-muted mb-2" style={{ fontSize: '0.7rem' }}>
                                      {item.data_dal || '—'}
                                      {item.data_al && <span className="d-block">→ {item.data_al}</span>}
                                    </div>

                                    {/* Card */}
                                    <div
                                      className={`card border-0 shadow-sm ${!item.is_active ? 'opacity-75' : ''}`}
                                      style={{
                                        borderRadius: '12px',
                                        background: item.is_active ? '#fff' : '#f8fafc',
                                      }}
                                    >
                                      <div className="card-body p-2">
                                        {/* Status badge */}
                                        <div className="mb-2">
                                          {item.is_active ? (
                                            <span className="badge bg-success" style={{ fontSize: '0.65rem' }}>Attivo</span>
                                          ) : (
                                            <span className="badge bg-secondary" style={{ fontSize: '0.65rem' }}>Concluso</span>
                                          )}
                                        </div>

                                        {/* Avatar */}
                                        <div className="d-flex justify-content-center mb-2">
                                          {item.avatar_path ? (
                                            <img
                                              src={item.avatar_path}
                                              alt=""
                                              className="rounded-circle"
                                              style={{ width: '36px', height: '36px', objectFit: 'cover' }}
                                            />
                                          ) : (
                                            <div
                                              className="rounded-circle bg-success text-white d-flex align-items-center justify-content-center"
                                              style={{ width: '36px', height: '36px', fontSize: '0.75rem' }}
                                            >
                                              {item.professionista_nome?.split(' ').map(n => n[0]).join('').substring(0,2).toUpperCase() || '??'}
                                            </div>
                                          )}
                                        </div>

                                        {/* Name */}
                                        <div className="fw-semibold small" style={{
                                          fontSize: '0.8rem',
                                          whiteSpace: 'nowrap',
                                          overflow: 'hidden',
                                          textOverflow: 'ellipsis',
                                        }}>
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
                      <div className="col-md-6">
                        <h6 className="text-uppercase text-muted small fw-semibold mb-3">
                          Stato Servizio
                        </h6>
                        <div className="card border">
                          <div className="card-body p-3">
                            <div className="d-flex align-items-center mb-3">
                              <div className="bg-success-subtle rounded-circle d-flex align-items-center justify-content-center me-2" style={{ width: '28px', height: '28px' }}>
                                <i className="ri-heart-pulse-line text-success" style={{ fontSize: '0.85rem' }}></i>
                              </div>
                              <span className="fw-semibold" style={{ fontSize: '0.9rem' }}>Stato Nutrizione</span>
                            </div>
                            <select
                              className="form-select form-select-sm mb-2"
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
                              <small className="text-muted" style={{ fontSize: '0.7rem' }}>
                                <i className="ri-calendar-line me-1"></i>
                                Ultimo cambio: {new Date(c.stato_nutrizione_data).toLocaleDateString('it-IT')}
                              </small>
                            )}
                          </div>
                        </div>
                      </div>

                      <div className="col-md-6">
                        <h6 className="text-uppercase text-muted small fw-semibold mb-3">
                          Stato Chat
                        </h6>
                        <div className="card border">
                          <div className="card-body p-3">
                            <div className="d-flex align-items-center mb-3">
                              <div className="bg-warning-subtle rounded-circle d-flex align-items-center justify-content-center me-2" style={{ width: '28px', height: '28px' }}>
                                <i className="ri-chat-3-line text-warning" style={{ fontSize: '0.85rem' }}></i>
                              </div>
                              <span className="fw-semibold" style={{ fontSize: '0.9rem' }}>Stato Chat Nutrizione</span>
                            </div>
                            <select
                              className="form-select form-select-sm mb-2"
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
                      <div className="col-12" data-tour="nutrizione-storico">
                        <h6 className="text-uppercase text-muted small fw-semibold mb-3">
                          <i className="ri-history-line me-2"></i>
                          Storico Stati (Servizio + Chat)
                        </h6>
                        {loadingStoricoNutrizione ? (
                          <div className="text-center py-4">
                            <div className="spinner-border spinner-border-sm text-success" role="status"></div>
                            <small className="ms-2 text-muted">Caricamento storico...</small>
                          </div>
                        ) : (storicoStatoNutrizione.length > 0 || storicoChatNutrizione.length > 0) ? (
                            <div className="timeline-horizontal" style={{
                              overflowX: 'auto',
                              paddingBottom: '10px',
                              position: 'relative',
                            }}>
                              {/* Horizontal line */}
                              <div style={{
                                position: 'absolute',
                                left: '0',
                                right: '0',
                                top: '24px',
                                height: '3px',
                                background: 'linear-gradient(to right, #22c55e, #f59e0b)',
                                borderRadius: '2px',
                                zIndex: 0,
                              }}></div>

                              <div className="d-flex gap-3 align-items-start" style={{ minWidth: 'max-content', position: 'relative', zIndex: 1 }}>
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
                                    const bgColor = isServizio ? 'success' : 'warning';
                                    const icon = isServizio ? 'ri-heart-pulse-line' : 'ri-chat-3-line';

                                    return (
                                      <div key={idx} className="timeline-item-h text-center" style={{ minWidth: '130px', maxWidth: '150px' }}>
                                        {/* Dot on line */}
                                        <div className="d-flex justify-content-center mb-2">
                                          <div
                                            className={`rounded-circle d-flex align-items-center justify-content-center bg-${bgColor}`}
                                            style={{
                                              width: '28px',
                                              height: '28px',
                                              border: '3px solid #fff',
                                              boxShadow: '0 2px 8px rgba(0,0,0,0.15)',
                                            }}
                                          >
                                            <i className={`${icon} text-white`} style={{ fontSize: '0.75rem' }}></i>
                                          </div>
                                        </div>

                                        {/* Date label */}
                                        <div className="small text-muted mb-2" style={{ fontSize: '0.7rem' }}>
                                          {item.data_inizio || '—'}
                                          {item.data_fine && <span className="d-block">→ {item.data_fine}</span>}
                                        </div>

                                        {/* Card */}
                                        <div
                                          className={`card border-0 shadow-sm ${!item.is_attivo ? 'opacity-75' : ''}`}
                                          style={{
                                            borderRadius: '12px',
                                            background: item.is_attivo ? '#fff' : '#f8fafc',
                                          }}
                                        >
                                          <div className="card-body p-2">
                                            {/* Type badge */}
                                            <div className="mb-1">
                                              <span className={`badge bg-${bgColor}-subtle text-${bgColor}`} style={{ fontSize: '0.6rem' }}>
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
                                              <div className="text-success" style={{ fontSize: '0.65rem' }}>
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
                          <div className="card border">
                            <div className="card-body p-3 text-center text-muted">
                              <i className="ri-history-line fs-3 d-block mb-2 opacity-50"></i>
                              <p className="mb-0 small">Nessuno storico stati disponibile</p>
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
                    <div className="col-12" data-tour="nutrizione-setup">
                      <div className="row g-4">
                      {/* Call Iniziale */}
                      <div className="col-12">
                        <h6 className="text-uppercase text-muted small fw-semibold mb-3">
                          Call Iniziale
                        </h6>
                        <div className="card border">
                          <div className="card-body p-3">
                            <div className="d-flex align-items-center mb-3">
                              <div className="bg-primary-subtle rounded-circle d-flex align-items-center justify-content-center me-2" style={{ width: '28px', height: '28px' }}>
                                <i className="ri-phone-line text-primary" style={{ fontSize: '0.85rem' }}></i>
                              </div>
                              <span className="fw-semibold" style={{ fontSize: '0.9rem' }}>Call Iniziale Nutrizionista</span>
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
                                <span className="badge bg-success ms-2" style={{ fontSize: '0.65rem' }}>Completata</span>
                              )}
                            </div>
                            {formData.call_iniziale_nutrizionista && (
                              <div className="mt-3">
                                <label className="form-label small text-muted mb-1">Data Call</label>
                                <input
                                  type="date"
                                  className="form-control form-control-sm"
                                  value={formData.data_call_iniziale_nutrizionista || ''}
                                  onChange={(e) => handleInputChange('data_call_iniziale_nutrizionista', e.target.value)}
                                />
                              </div>
                            )}
                          </div>
                        </div>
                      </div>

                      {/* Reach Out */}
                      <div className="col-12">
                        <h6 className="text-uppercase text-muted small fw-semibold mb-3">
                          Reach Out Settimanale
                        </h6>
                        <div className="card border">
                          <div className="card-body p-3">
                            <div className="d-flex align-items-center mb-3">
                              <div className="bg-info-subtle rounded-circle d-flex align-items-center justify-content-center me-2" style={{ width: '28px', height: '28px' }}>
                                <i className="ri-calendar-check-line text-info" style={{ fontSize: '0.85rem' }}></i>
                              </div>
                              <span className="fw-semibold" style={{ fontSize: '0.9rem' }}>Giorno Reach Out</span>
                            </div>
                            <select
                              className="form-select form-select-sm"
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
                              <small className="text-muted d-block mt-2" style={{ fontSize: '0.7rem' }}>
                                <i className="ri-calendar-event-line me-1"></i>
                                Reach out ogni {
                                  { lunedi: 'Lunedì', martedi: 'Martedì', mercoledi: 'Mercoledì', giovedi: 'Giovedì', venerdi: 'Venerdì', sabato: 'Sabato', domenica: 'Domenica' }[formData.reach_out_nutrizione]
                                }
                              </small>
                            )}
                          </div>
                        </div>
                      </div>
                      </div>
                    </div>
                  )}

                  {/* ===== PATOLOGIE SUB-TAB ===== */}
                  {nutrizioneSubTab === 'patologie' && (
                    <div className="col-12" data-tour="nutrizione-patologie">
                      <div className="row g-4">
                      <div className="col-12">
                        <h6 className="text-uppercase text-muted small fw-semibold mb-3">
                          Patologie del Cliente
                        </h6>
                        <div className="card border">
                          <div className="card-body p-3">
                            <div className="d-flex align-items-center mb-3">
                              <div className="bg-warning-subtle rounded-circle d-flex align-items-center justify-content-center me-2" style={{ width: '28px', height: '28px' }}>
                                <i className="ri-stethoscope-line text-warning" style={{ fontSize: '0.85rem' }}></i>
                              </div>
                              <span className="fw-semibold" style={{ fontSize: '0.9rem' }}>Patologie Nutrizionali</span>
                            </div>

                            {/* Nessuna Patologia - in evidenza */}
                            <div
                              className={`p-2 rounded mb-3 border ${formData.nessuna_patologia ? 'bg-success-subtle border-success' : 'border-secondary'}`}
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
                            <div className="row g-1">
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
                                <div key={key} className="col-md-4 col-6">
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
                              <div className="col-md-4 col-6">
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
                                  className="form-control form-control-sm"
                                  placeholder="Specifica altra patologia..."
                                  value={formData.patologia_altro || ''}
                                  onChange={(e) => handleInputChange('patologia_altro', e.target.value)}
                                />
                              </div>
                            )}
                          </div>
                        </div>
                      </div>

                      {/* ===== ANAMNESI MERGED ===== */}
                      <div className="col-12">
                        <h6 className="text-uppercase text-muted small fw-semibold mb-3">
                          Anamnesi Nutrizionale
                        </h6>
                        <div className="card border">
                          <div className="card-body p-3">
                            <div className="d-flex align-items-center justify-content-between mb-3">
                              <div className="d-flex align-items-center">
                                <div className="rounded-circle d-flex align-items-center justify-content-center me-2" style={{ width: '28px', height: '28px', background: '#f3e8ff' }}>
                                  <i className="ri-file-list-3-line" style={{ fontSize: '0.85rem', color: '#8b5cf6' }}></i>
                                </div>
                                <span className="fw-semibold" style={{ fontSize: '0.9rem' }}>Valutazione Iniziale</span>
                              </div>
                              <button
                                className="btn btn-sm btn-primary"
                                onClick={handleSaveAnamnesi}
                                disabled={savingAnamnesi || loadingAnamnesi}
                              >
                                {savingAnamnesi ? (
                                  <><span className="spinner-border spinner-border-sm me-1"></span>Salvataggio...</>
                                ) : (
                                  <><i className="ri-save-line me-1"></i>Salva</>
                                )}
                              </button>
                            </div>

                            {loadingAnamnesi ? (
                              <div className="text-center py-4">
                                <div className="spinner-border spinner-border-sm text-primary" role="status"></div>
                                <small className="ms-2 text-muted">Caricamento anamnesi...</small>
                              </div>
                            ) : (
                              <>
                                <textarea
                                  className="form-control mb-3"
                                  rows="10"
                                  placeholder="Inserisci l'anamnesi nutrizionale del cliente...&#10;&#10;• Storia clinica&#10;• Abitudini alimentari&#10;• Obiettivi&#10;• Allergie e intolleranze&#10;• Farmaci in uso&#10;• Attività fisica&#10;• Stile di vita"
                                  value={anamnesiContent}
                                  onChange={(e) => setAnamnesiContent(e.target.value)}
                                ></textarea>
                                {anamnesiNutrizione && (
                                  <div className="small text-muted border-top pt-2">
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
                    <div className="col-12" data-tour="nutrizione-piani-wrapper">
                      <div className="row g-4">
                      {/* Piano Attivo */}
                      <div className="col-12" data-tour="nutrizione-piani">
                        <h6 className="text-uppercase text-muted small fw-semibold mb-3">
                          Piano Alimentare Attivo
                        </h6>
                        {loadingMealPlans ? (
                          <div className="text-center py-4">
                            <div className="spinner-border spinner-border-sm text-success" role="status"></div>
                            <small className="ms-2 text-muted">Caricamento piani...</small>
                          </div>
                        ) : (
                          <div className="card border">
                            <div className="card-body p-3">
                              <div className="d-flex align-items-center justify-content-between mb-3">
                                <div className="d-flex align-items-center">
                                  <div className="bg-success-subtle rounded-circle d-flex align-items-center justify-content-center me-2" style={{ width: '28px', height: '28px' }}>
                                    <i className="ri-restaurant-line text-success" style={{ fontSize: '0.85rem' }}></i>
                                  </div>
                                  <span className="fw-semibold" style={{ fontSize: '0.9rem' }}>Piano Corrente</span>
                                </div>
                                <button
                                  className="btn btn-sm btn-success"
                                  onClick={() => setShowAddMealPlanModal(true)}
                                >
                                  <i className="ri-add-line me-1"></i>
                                  Nuovo Piano
                                </button>
                              </div>

                              {(() => {
                                const activePlan = mealPlans.find(p => p.is_active);
                                if (activePlan) {
                                  return (
                                    <div className="p-3 rounded-3 bg-success-subtle">
                                      <div className="d-flex justify-content-between align-items-start mb-2">
                                        <div>
                                          <h6 className="mb-1 fw-semibold">{activePlan.name || 'Piano Alimentare'}</h6>
                                          <small className="text-muted">
                                            <i className="ri-calendar-line me-1"></i>
                                            {activePlan.start_date ? new Date(activePlan.start_date).toLocaleDateString('it-IT') : '-'}
                                            {' → '}
                                            {activePlan.end_date ? new Date(activePlan.end_date).toLocaleDateString('it-IT') : '-'}
                                            {activePlan.duration_days && (
                                              <span className="ms-2">({activePlan.duration_days} giorni)</span>
                                            )}
                                          </small>
                                        </div>
                                        <span className="badge bg-success">Attivo</span>
                                      </div>

                                      {activePlan.notes && (
                                        <p className="small text-muted mb-2 mt-2">
                                          <i className="ri-sticky-note-line me-1"></i>
                                          {activePlan.notes}
                                        </p>
                                      )}

                                      <div className="d-flex gap-2 mt-3 flex-wrap">
                                        {activePlan.has_file && activePlan.piano_alimentare_file_path && (
                                          <button
                                            className="btn btn-sm btn-success"
                                            onClick={() => handlePreviewPlan(activePlan)}
                                          >
                                            <i className="ri-eye-line me-1"></i>
                                            Visualizza
                                          </button>
                                        )}
                                        <button
                                          className="btn btn-sm btn-outline-primary"
                                          onClick={() => handleOpenEditPlan(activePlan)}
                                        >
                                          <i className="ri-edit-line me-1"></i>
                                          Modifica
                                        </button>
                                        <button
                                          className="btn btn-sm btn-outline-secondary"
                                          onClick={() => handleViewVersions(activePlan)}
                                        >
                                          <i className="ri-history-line me-1"></i>
                                          Storico
                                        </button>
                                        {activePlan.extra_files && activePlan.extra_files.length > 0 && (
                                          <span className="badge bg-secondary align-self-center">
                                            +{activePlan.extra_files.length} file extra
                                          </span>
                                        )}
                                      </div>
                                    </div>
                                  );
                                } else {
                                  return (
                                    <p className="text-muted small mb-0">
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
                        <div className="col-12">
                          <h6 className="text-uppercase text-muted small fw-semibold mb-3">
                            <i className="ri-history-line me-2"></i>
                            Storico Piani Alimentari
                          </h6>
                          <div className="card border">
                            <div className="card-body p-3">
                              <div className="d-flex align-items-center mb-3">
                                <div className="bg-secondary-subtle rounded-circle d-flex align-items-center justify-content-center me-2" style={{ width: '28px', height: '28px' }}>
                                  <i className="ri-archive-line text-secondary" style={{ fontSize: '0.85rem' }}></i>
                                </div>
                                <span className="fw-semibold" style={{ fontSize: '0.9rem' }}>Piani Precedenti</span>
                                <span className="badge bg-secondary ms-auto">{mealPlans.filter(p => !p.is_active).length}</span>
                              </div>

                              <div className="table-responsive">
                                <table className="table table-sm table-hover mb-0" style={{ fontSize: '0.85rem' }}>
                                  <thead>
                                    <tr className="text-muted">
                                      <th style={{ fontWeight: '500' }}>Nome</th>
                                      <th style={{ fontWeight: '500' }}>Periodo</th>
                                      <th style={{ fontWeight: '500' }}>Durata</th>
                                      <th style={{ fontWeight: '500' }} className="text-end">Azioni</th>
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
                                              <span className="badge bg-warning-subtle text-warning ms-2" style={{ fontSize: '0.65rem' }}>Legacy</span>
                                            )}
                                          </td>
                                          <td className="text-muted">
                                            {plan.start_date ? new Date(plan.start_date).toLocaleDateString('it-IT') : '-'}
                                            {' → '}
                                            {plan.end_date ? new Date(plan.end_date).toLocaleDateString('it-IT') : '-'}
                                          </td>
                                          <td className="text-muted">
                                            {plan.duration_days ? `${plan.duration_days}gg` : '-'}
                                          </td>
                                          <td className="text-end">
                                            <div className="d-flex gap-1 justify-content-end">
                                              {plan.has_file && plan.piano_alimentare_file_path && (
                                                <>
                                                  <button
                                                    className="btn btn-sm btn-outline-success py-0 px-2"
                                                    onClick={() => handlePreviewPlan(plan)}
                                                    title="Visualizza"
                                                  >
                                                    <i className="ri-eye-line"></i>
                                                  </button>
                                                  <a
                                                    href={`/uploads/${plan.piano_alimentare_file_path}`}
                                                    target="_blank"
                                                    rel="noopener noreferrer"
                                                    className="btn btn-sm btn-outline-success py-0 px-2"
                                                    title="Scarica"
                                                  >
                                                    <i className="ri-download-line"></i>
                                                  </a>
                                                </>
                                              )}
                                              {!plan.is_legacy && (
                                                <>
                                                  <button
                                                    className="btn btn-sm btn-outline-primary py-0 px-2"
                                                    onClick={() => handleOpenEditPlan(plan)}
                                                    title="Modifica"
                                                  >
                                                    <i className="ri-edit-line"></i>
                                                  </button>
                                                  <button
                                                    className="btn btn-sm btn-outline-secondary py-0 px-2"
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
                        <div className="col-12">
                          <h6 className="text-uppercase text-muted small fw-semibold mb-3">
                            Date Riferimento
                          </h6>
                          <div className="card border">
                            <div className="card-body p-3">
                              <div className="d-flex align-items-center mb-3">
                                <div className="bg-info-subtle rounded-circle d-flex align-items-center justify-content-center me-2" style={{ width: '28px', height: '28px' }}>
                                  <i className="ri-calendar-2-line text-info" style={{ fontSize: '0.85rem' }}></i>
                                </div>
                                <span className="fw-semibold" style={{ fontSize: '0.9rem' }}>Date Dieta Cliente</span>
                              </div>
                              <div className="row g-3">
                                <div className="col-md-6">
                                  <label className="form-label small text-muted mb-1">Dieta Dal</label>
                                  <input
                                    type="date"
                                    className="form-control form-control-sm"
                                    value={formData.dieta_dal || ''}
                                    onChange={(e) => handleInputChange('dieta_dal', e.target.value)}
                                  />
                                </div>
                                <div className="col-md-6">
                                  <label className="form-label small text-muted mb-1">Nuova Dieta Dal</label>
                                  <input
                                    type="date"
                                    className="form-control form-control-sm"
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
                    <div className="col-12" data-tour="nutrizione-diario">
                      <div className="row g-4">
                      <div className="col-12">
                        <h6 className="text-uppercase text-muted small fw-semibold mb-3">
                          Diario Nutrizionale
                        </h6>
                        <div className="card border">
                          <div className="card-body p-3">
                            <div className="d-flex align-items-center justify-content-between mb-3">
                              <div className="d-flex align-items-center">
                                <div className="rounded-circle d-flex align-items-center justify-content-center me-2" style={{ width: '28px', height: '28px', background: '#fce7f3' }}>
                                  <i className="ri-book-2-line" style={{ fontSize: '0.85rem', color: '#ec4899' }}></i>
                                </div>
                                <span className="fw-semibold" style={{ fontSize: '0.9rem' }}>Note del Percorso</span>
                                <span className="badge bg-secondary ms-2">{diarioEntries.length}</span>
                              </div>
                              <button
                                className="btn btn-sm btn-primary"
                                onClick={() => handleOpenDiarioModal()}
                              >
                                <i className="ri-add-line me-1"></i>
                                Nuova Nota
                              </button>
                            </div>

                            {loadingDiario ? (
                              <div className="text-center py-4">
                                <div className="spinner-border spinner-border-sm text-primary" role="status"></div>
                                <small className="ms-2 text-muted">Caricamento diario...</small>
                              </div>
                            ) : diarioEntries.length === 0 ? (
                              <p className="text-muted small mb-0 text-center py-3">
                                <i className="ri-information-line me-1"></i>
                                Nessuna nota nel diario. Clicca "Nuova Nota" per aggiungerne una.
                              </p>
                            ) : (
                              <div className="d-flex flex-column gap-3">
                                {diarioEntries.map((entry) => (
                                  <div key={entry.id} className="border rounded-3 p-3" style={{ background: '#fafafa' }}>
                                    <div className="d-flex justify-content-between align-items-start mb-2">
                                      <div>
                                        <span className="badge bg-primary-subtle text-primary me-2">
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
                                      <div className="d-flex gap-1">
                                        <button
                                          className="btn btn-sm btn-outline-primary py-0 px-2"
                                          onClick={() => handleOpenDiarioModal(entry)}
                                          title="Modifica"
                                        >
                                          <i className="ri-edit-line"></i>
                                        </button>
                                        {(user?.is_admin || user?.role === 'admin') && (
                                          <button
                                            className="btn btn-sm btn-outline-danger py-0 px-2"
                                            onClick={() => handleDeleteDiarioEntry(entry.id)}
                                            title="Elimina"
                                          >
                                            <i className="ri-delete-bin-line"></i>
                                          </button>
                                        )}
                                        <button
                                          className="btn btn-sm btn-outline-secondary py-0 px-2"
                                          onClick={() => handleOpenHistoryModal(entry, 'nutrizione')}
                                          title="Storico Modifiche"
                                        >
                                          <i className="ri-history-line"></i>
                                        </button>
                                      </div>
                                    </div>
                                    <p className="mb-0 small" style={{ whiteSpace: 'pre-wrap' }}>{entry.content}</p>
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
                    <div className="col-12" data-tour="nutrizione-alert">
                      <div className="row g-4">
                      <div className="col-12">
                        <h6 className="text-uppercase text-muted small fw-semibold mb-3">
                          Alert e Criticità
                        </h6>
                        <div className="card border border-danger">
                          <div className="card-body p-3">
                            <div className="d-flex align-items-center mb-3">
                              <div className="bg-danger-subtle rounded-circle d-flex align-items-center justify-content-center me-2" style={{ width: '28px', height: '28px' }}>
                                <i className="ri-alarm-warning-line text-danger" style={{ fontSize: '0.85rem' }}></i>
                              </div>
                              <span className="fw-semibold text-danger" style={{ fontSize: '0.9rem' }}>Alert Nutrizione</span>
                            </div>
                            <p className="text-muted small mb-2">
                              Informazioni critiche: allergie, intolleranze, controindicazioni alimentari.
                              Queste note saranno sempre visibili in evidenza.
                            </p>
                            <textarea
                              className="form-control border-danger"
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
                </div>
              )}

              {/* ========== COACHING TAB ========== */}
              {activeTab === 'coaching' && (
                <div className="row g-4">
                  {/* Sub-tab Navigation */}
                  <div className="col-12" data-tour="coaching-subtabs">
                    <div style={{ overflowX: 'auto', overflowY: 'hidden', WebkitOverflowScrolling: 'touch', scrollbarWidth: 'none', msOverflowStyle: 'none' }}>
                      <ul className="nav nav-pills mb-0" style={{ gap: '8px', flexWrap: 'nowrap', minWidth: 'max-content' }}>
                        {[
                          { key: 'panoramica', label: 'Panoramica', icon: 'ri-dashboard-line', color: '#f59e0b' },
                          { key: 'setup', label: 'Setup', icon: 'ri-settings-3-line', color: '#3b82f6' },
                          { key: 'piano', label: 'Piano Allenamento', icon: 'ri-run-line', color: '#f59e0b' },
                          { key: 'luoghi', label: 'Luoghi', icon: 'ri-map-pin-line', color: '#10b981' },
                          { key: 'patologie', label: 'Patologie', icon: 'ri-stethoscope-line', color: '#f59e0b' },
                          { key: 'diario', label: 'Diario', icon: 'ri-book-2-line', color: '#ec4899' },
                          { key: 'alert', label: 'Alert', icon: 'ri-alarm-warning-line', color: '#ef4444' },
                        ].map(({ key, label, icon, color }) => (
                          <li key={key} className="nav-item">
                            <button
                              className="nav-link"
                              onClick={() => setCoachingSubTab(key)}
                              style={{
                                background: coachingSubTab === key ? `linear-gradient(135deg, ${color} 0%, ${color}dd 100%)` : '#f1f5f9',
                                color: coachingSubTab === key ? '#fff' : '#64748b',
                                border: 'none',
                                borderRadius: '8px',
                                padding: '8px 16px',
                                fontWeight: 600,
                                fontSize: '0.85rem',
                                whiteSpace: 'nowrap',
                              }}
                            >
                              <i className={`${icon} me-1`}></i>
                              {label}
                            </button>
                          </li>
                        ))}
                      </ul>
                    </div>
                  </div>

                  {/* ===== PANORAMICA SUB-TAB ===== */}
                  {coachingSubTab === 'panoramica' && (
                    <div className="col-12" data-tour="coaching-panoramica">
                      <div className="row g-4">
                      {/* Coach Assegnati - Same style as Nutrizione */}
                      <div className="col-12">
                        <h6 className="text-uppercase text-muted small fw-semibold mb-3">
                          Coach Assegnati
                        </h6>
                        {loadingHistory ? (
                          <div className="text-center py-4">
                            <div className="spinner-border spinner-border-sm text-warning" role="status"></div>
                            <small className="ms-2 text-muted">Caricamento...</small>
                          </div>
                        ) : (
                          <div className="card border">
                            <div className="card-body p-3">
                              <div className="d-flex align-items-center justify-content-between mb-3">
                                <div className="d-flex align-items-center">
                                  <div className="bg-warning-subtle rounded-circle d-flex align-items-center justify-content-center me-2"
                                       style={{ width: '32px', height: '32px' }}>
                                    <i className="ri-run-line text-warning"></i>
                                  </div>
                                  <span className="fw-semibold">Team Coaching</span>
                                </div>
                                <span className="badge bg-warning">{getActiveProfessionals('coach').length} attivi</span>
                              </div>

                              {getActiveProfessionals('coach').length > 0 ? (
                                <div className="d-flex flex-wrap gap-2">
                                  {getActiveProfessionals('coach').map((assignment, idx) => (
                                    <div key={idx} className="d-flex align-items-center p-2 bg-light rounded">
                                      {assignment.avatar_path ? (
                                        <img src={assignment.avatar_path} alt="" className="rounded-circle me-2" style={{ width: '32px', height: '32px', objectFit: 'cover' }} />
                                      ) : (
                                        <div className="rounded-circle bg-warning text-white d-flex align-items-center justify-content-center me-2" style={{ width: '32px', height: '32px', fontSize: '0.75rem' }}>
                                          {assignment.professionista_nome?.split(' ').map(n => n[0]).join('').substring(0,2).toUpperCase() || '??'}
                                        </div>
                                      )}
                                      <div>
                                        <small className="d-block fw-medium">{assignment.professionista_nome}</small>
                                        <small className="text-muted" style={{ fontSize: '0.7rem' }}>dal {assignment.data_dal}</small>
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
                        <div className="col-12">
                          <h6 className="text-uppercase text-muted small fw-semibold mb-3">
                            <i className="ri-history-line me-2"></i>
                            Storico Assegnazioni
                          </h6>
                          <div className="timeline-horizontal" style={{
                            overflowX: 'auto',
                            paddingBottom: '10px',
                            position: 'relative',
                          }}>
                            {/* Horizontal line */}
                            <div style={{
                              position: 'absolute',
                              left: '0',
                              right: '0',
                              top: '24px',
                              height: '3px',
                              background: 'linear-gradient(to right, #f59e0b, #d97706)',
                              borderRadius: '2px',
                              zIndex: 0,
                            }}></div>

                            <div className="d-flex gap-3 align-items-start" style={{ minWidth: 'max-content', position: 'relative', zIndex: 1 }}>
                              {professionistiHistory
                                .filter(h => h.tipo_professionista === 'coach')
                                .sort((a, b) => {
                                  const dateA = new Date(a.data_dal?.split('/').reverse().join('-') || 0);
                                  const dateB = new Date(b.data_dal?.split('/').reverse().join('-') || 0);
                                  return dateB - dateA;
                                })
                                .map((item, idx) => (
                                  <div key={idx} className="timeline-item-h text-center" style={{ minWidth: '140px', maxWidth: '160px' }}>
                                    {/* Dot on line */}
                                    <div className="d-flex justify-content-center mb-2">
                                      <div
                                        className="rounded-circle d-flex align-items-center justify-content-center bg-warning"
                                        style={{
                                          width: '28px',
                                          height: '28px',
                                          border: '3px solid #fff',
                                          boxShadow: '0 2px 8px rgba(0,0,0,0.15)',
                                        }}
                                      >
                                        <i className="ri-run-line text-white" style={{ fontSize: '0.75rem' }}></i>
                                      </div>
                                    </div>

                                    {/* Date label */}
                                    <div className="small text-muted mb-2" style={{ fontSize: '0.7rem' }}>
                                      {item.data_dal || '—'}
                                      {item.data_al && <span className="d-block">→ {item.data_al}</span>}
                                    </div>

                                    {/* Card */}
                                    <div
                                      className={`card border-0 shadow-sm ${!item.is_active ? 'opacity-75' : ''}`}
                                      style={{
                                        borderRadius: '12px',
                                        background: item.is_active ? '#fff' : '#f8fafc',
                                      }}
                                    >
                                      <div className="card-body p-2">
                                        {/* Status badge */}
                                        <div className="mb-2">
                                          {item.is_active ? (
                                            <span className="badge bg-warning" style={{ fontSize: '0.65rem' }}>Attivo</span>
                                          ) : (
                                            <span className="badge bg-secondary" style={{ fontSize: '0.65rem' }}>Concluso</span>
                                          )}
                                        </div>

                                        {/* Avatar */}
                                        <div className="d-flex justify-content-center mb-2">
                                          {item.avatar_path ? (
                                            <img
                                              src={item.avatar_path}
                                              alt=""
                                              className="rounded-circle"
                                              style={{ width: '36px', height: '36px', objectFit: 'cover' }}
                                            />
                                          ) : (
                                            <div
                                              className="rounded-circle bg-warning text-white d-flex align-items-center justify-content-center"
                                              style={{ width: '36px', height: '36px', fontSize: '0.75rem' }}
                                            >
                                              {item.professionista_nome?.split(' ').map(n => n[0]).join('').substring(0,2).toUpperCase() || '??'}
                                            </div>
                                          )}
                                        </div>

                                        {/* Name */}
                                        <div className="fw-semibold small" style={{
                                          fontSize: '0.8rem',
                                          whiteSpace: 'nowrap',
                                          overflow: 'hidden',
                                          textOverflow: 'ellipsis',
                                        }}>
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
                      <div className="col-md-6">
                        <h6 className="text-uppercase text-muted small fw-semibold mb-3">
                          Stato Servizio
                        </h6>
                        <div className="card border">
                          <div className="card-body p-3">
                            <div className="d-flex align-items-center mb-3">
                              <div className="bg-warning-subtle rounded-circle d-flex align-items-center justify-content-center me-2" style={{ width: '28px', height: '28px' }}>
                                <i className="ri-run-line text-warning" style={{ fontSize: '0.85rem' }}></i>
                              </div>
                              <span className="fw-semibold" style={{ fontSize: '0.9rem' }}>Stato Coaching</span>
                            </div>
                            <select
                              className="form-select form-select-sm mb-2"
                              value={formData.stato_coach || ''}
                              onChange={(e) => handleInputChange('stato_coach', e.target.value)}
                            >
                              <option value="">Seleziona stato...</option>
                              <option value="attivo">Attivo</option>
                              <option value="pausa">Pausa</option>
                              <option value="ghost">Ghost</option>
                              <option value="stop">Ex-Cliente</option>
                            </select>
                            {c.stato_coach_data && (
                              <small className="text-muted" style={{ fontSize: '0.7rem' }}>
                                <i className="ri-calendar-line me-1"></i>
                                Ultimo cambio: {new Date(c.stato_coach_data).toLocaleDateString('it-IT')}
                              </small>
                            )}
                          </div>
                        </div>
                      </div>

                      <div className="col-md-6">
                        <h6 className="text-uppercase text-muted small fw-semibold mb-3">
                          Stato Chat
                        </h6>
                        <div className="card border">
                          <div className="card-body p-3">
                            <div className="d-flex align-items-center mb-3">
                              <div className="bg-secondary-subtle rounded-circle d-flex align-items-center justify-content-center me-2" style={{ width: '28px', height: '28px' }}>
                                <i className="ri-chat-3-line text-secondary" style={{ fontSize: '0.85rem' }}></i>
                              </div>
                              <span className="fw-semibold" style={{ fontSize: '0.9rem' }}>Stato Chat Coaching</span>
                            </div>
                            <select
                              className="form-select form-select-sm mb-2"
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

                      {/* Timeline Storico Stati Unificata */}
                      <div className="col-12">
                        <h6 className="text-uppercase text-muted small fw-semibold mb-3">
                          <i className="ri-history-line me-2"></i>
                          Storico Stati (Servizio + Chat)
                        </h6>
                        {loadingStoricoCoaching ? (
                          <div className="text-center py-4">
                            <div className="spinner-border spinner-border-sm text-warning" role="status"></div>
                            <small className="ms-2 text-muted">Caricamento storico...</small>
                          </div>
                        ) : (storicoStatoCoaching.length > 0 || storicoChatCoaching.length > 0) ? (
                            <div className="timeline-horizontal" style={{
                              overflowX: 'auto',
                              paddingBottom: '10px',
                              position: 'relative',
                            }}>
                              {/* Horizontal line */}
                              <div style={{
                                position: 'absolute',
                                left: '0',
                                right: '0',
                                top: '24px',
                                height: '3px',
                                background: 'linear-gradient(to right, #f59e0b, #6b7280)',
                                borderRadius: '2px',
                                zIndex: 0,
                              }}></div>

                              <div className="d-flex gap-3 align-items-start" style={{ minWidth: 'max-content', position: 'relative', zIndex: 1 }}>
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

                                    return (
                                      <div key={idx} className="timeline-item-h text-center" style={{ minWidth: '130px', maxWidth: '150px' }}>
                                        {/* Dot on line */}
                                        <div className="d-flex justify-content-center mb-2">
                                          <div
                                            className={`rounded-circle d-flex align-items-center justify-content-center bg-${bgColor}`}
                                            style={{
                                              width: '28px',
                                              height: '28px',
                                              border: '3px solid #fff',
                                              boxShadow: '0 2px 8px rgba(0,0,0,0.15)',
                                            }}
                                          >
                                            <i className={`${icon} text-white`} style={{ fontSize: '0.75rem' }}></i>
                                          </div>
                                        </div>

                                        {/* Date label */}
                                        <div className="small text-muted mb-2" style={{ fontSize: '0.7rem' }}>
                                          {item.data_inizio || '—'}
                                          {item.data_fine && <span className="d-block">→ {item.data_fine}</span>}
                                        </div>

                                        {/* Card */}
                                        <div
                                          className={`card border-0 shadow-sm ${!item.is_attivo ? 'opacity-75' : ''}`}
                                          style={{
                                            borderRadius: '12px',
                                            background: item.is_attivo ? '#fff' : '#f8fafc',
                                          }}
                                        >
                                          <div className="card-body p-2">
                                            {/* Type badge */}
                                            <div className="mb-1">
                                              <span className={`badge bg-${bgColor}-subtle text-${bgColor}`} style={{ fontSize: '0.6rem' }}>
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
                                              <div className="text-warning" style={{ fontSize: '0.65rem' }}>
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
                          <div className="card border">
                            <div className="card-body p-3 text-center text-muted">
                              <i className="ri-history-line fs-3 d-block mb-2 opacity-50"></i>
                              <p className="mb-0 small">Nessuno storico stati disponibile</p>
                              <small>I cambi di stato verranno tracciati automaticamente</small>
                            </div>
                          </div>
                        )}
                      </div>

                      </div>
                    </div>
                  )}

                  {/* ===== SETUP SUB-TAB ===== */}
                  {coachingSubTab === 'setup' && (
                    <div className="col-12" data-tour="coaching-setup">
                      <div className="row g-4">
                      {/* Call Iniziale */}
                      <div className="col-12">
                        <h6 className="text-uppercase text-muted small fw-semibold mb-3">
                          Call Iniziale
                        </h6>
                        <div className="card border">
                          <div className="card-body p-3">
                            <div className="d-flex align-items-center mb-3">
                              <div className="bg-primary-subtle rounded-circle d-flex align-items-center justify-content-center me-2" style={{ width: '28px', height: '28px' }}>
                                <i className="ri-phone-line text-primary" style={{ fontSize: '0.85rem' }}></i>
                              </div>
                              <span className="fw-semibold" style={{ fontSize: '0.9rem' }}>Call Iniziale Coach</span>
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
                                <span className="badge bg-success ms-2" style={{ fontSize: '0.65rem' }}>Completata</span>
                              )}
                            </div>
                            {formData.call_iniziale_coach && (
                              <div className="mt-3">
                                <label className="form-label small text-muted mb-1">Data Call</label>
                                <input
                                  type="date"
                                  className="form-control form-control-sm"
                                  value={formData.data_call_iniziale_coach || ''}
                                  onChange={(e) => handleInputChange('data_call_iniziale_coach', e.target.value)}
                                />
                              </div>
                            )}
                          </div>
                        </div>
                      </div>

                      {/* Reach Out */}
                      <div className="col-12">
                        <h6 className="text-uppercase text-muted small fw-semibold mb-3">
                          Reach Out Settimanale
                        </h6>
                        <div className="card border">
                          <div className="card-body p-3">
                            <div className="d-flex align-items-center mb-3">
                              <div className="bg-info-subtle rounded-circle d-flex align-items-center justify-content-center me-2" style={{ width: '28px', height: '28px' }}>
                                <i className="ri-calendar-check-line text-info" style={{ fontSize: '0.85rem' }}></i>
                              </div>
                              <span className="fw-semibold" style={{ fontSize: '0.9rem' }}>Giorno Reach Out</span>
                            </div>
                            <select
                              className="form-select form-select-sm"
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
                            {formData.reach_out_coaching && (
                              <small className="text-muted d-block mt-2" style={{ fontSize: '0.7rem' }}>
                                <i className="ri-calendar-event-line me-1"></i>
                                Reach out ogni {
                                  { lunedi: 'Lunedì', martedi: 'Martedì', mercoledi: 'Mercoledì', giovedi: 'Giovedì', venerdi: 'Venerdì', sabato: 'Sabato', domenica: 'Domenica' }[formData.reach_out_coaching]
                                }
                              </small>
                            )}
                          </div>
                        </div>
                      </div>
                      </div>
                    </div>
                  )}

                  {/* ===== PIANO ALLENAMENTO SUB-TAB ===== */}
                  {coachingSubTab === 'piano' && (
                    <div className="col-12" data-tour="coaching-piani-wrapper">
                      <div className="row g-4">
                      <div className="col-12" data-tour="coaching-schede">
                        <h6 className="text-uppercase text-muted small fw-semibold mb-3">
                          Piano Allenamento Attivo
                        </h6>
                        {loadingTrainingPlans ? (
                          <div className="text-center py-4">
                            <div className="spinner-border spinner-border-sm text-warning" role="status"></div>
                            <small className="ms-2 text-muted">Caricamento piani...</small>
                          </div>
                        ) : (
                          <div className="card border">
                            <div className="card-body p-3">
                              <div className="d-flex align-items-center justify-content-between mb-3">
                                <div className="d-flex align-items-center">
                                  <div className="bg-warning-subtle rounded-circle d-flex align-items-center justify-content-center me-2" style={{ width: '28px', height: '28px' }}>
                                    <i className="ri-run-line text-warning" style={{ fontSize: '0.85rem' }}></i>
                                  </div>
                                  <span className="fw-semibold" style={{ fontSize: '0.9rem' }}>Piano Corrente</span>
                                </div>
                                <button
                                  className="btn btn-sm btn-warning"
                                  onClick={() => setShowAddTrainingPlanModal(true)}
                                >
                                  <i className="ri-add-line me-1"></i>
                                  Nuovo Piano
                                </button>
                              </div>
                              {(() => {
                                const activePlan = trainingPlans.find(p => p.is_active);
                                if (activePlan) {
                                  return (
                                    <div className="p-3 rounded-3 bg-warning-subtle">
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
                                        <span className="badge bg-warning">Attivo</span>
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
                                            className="btn btn-sm btn-warning"
                                            onClick={() => handlePreviewTrainingPlan(activePlan)}
                                          >
                                            <i className="ri-eye-line me-1"></i>
                                            Visualizza
                                          </button>
                                        )}
                                        <button
                                          className="btn btn-sm btn-outline-primary"
                                          onClick={() => handleOpenEditTrainingPlan(activePlan)}
                                        >
                                          <i className="ri-edit-line me-1"></i>
                                          Modifica
                                        </button>
                                        <button
                                          className="btn btn-sm btn-outline-secondary"
                                          onClick={() => handleViewTrainingVersions(activePlan)}
                                        >
                                          <i className="ri-history-line me-1"></i>
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
                        <div className="col-12">
                          <h6 className="text-uppercase text-muted small fw-semibold mb-3">
                            <i className="ri-history-line me-2"></i>
                            Storico Piani Allenamento
                          </h6>
                          <div className="card border">
                            <div className="card-body p-3">
                              <div className="table-responsive">
                                <table className="table table-sm table-hover mb-0" style={{ fontSize: '0.85rem' }}>
                                  <thead>
                                    <tr className="text-muted">
                                      <th style={{ fontWeight: '500' }}>Nome</th>
                                      <th style={{ fontWeight: '500' }}>Periodo</th>
                                      <th style={{ fontWeight: '500' }}>Durata</th>
                                      <th style={{ fontWeight: '500' }} className="text-end">Azioni</th>
                                    </tr>
                                  </thead>
                                  <tbody>
                                    {trainingPlans
                                      .filter(p => !p.is_active)
                                      .sort((a, b) => new Date(b.start_date) - new Date(a.start_date))
                                      .map((plan) => (
                                        <tr key={plan.id}>
                                          <td><span className="fw-medium">{plan.name || 'Piano Allenamento'}</span></td>
                                          <td className="text-muted">
                                            {plan.start_date ? new Date(plan.start_date).toLocaleDateString('it-IT') : '-'}
                                            {' → '}
                                            {plan.end_date ? new Date(plan.end_date).toLocaleDateString('it-IT') : '-'}
                                          </td>
                                          <td className="text-muted">{plan.duration_days ? `${plan.duration_days}gg` : '-'}</td>
                                          <td className="text-end">
                                            <div className="d-flex gap-1 justify-content-end">
                                              {plan.has_file && plan.piano_allenamento_file_path && (
                                                <button
                                                  className="btn btn-sm btn-outline-warning py-0 px-2"
                                                  onClick={() => handlePreviewTrainingPlan(plan)}
                                                  title="Visualizza"
                                                >
                                                  <i className="ri-eye-line"></i>
                                                </button>
                                              )}
                                              <button
                                                className="btn btn-sm btn-outline-primary py-0 px-2"
                                                onClick={() => handleOpenEditTrainingPlan(plan)}
                                                title="Modifica"
                                              >
                                                <i className="ri-edit-line"></i>
                                              </button>
                                              <button
                                                className="btn btn-sm btn-outline-secondary py-0 px-2"
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
                    <div className="col-12" data-tour="coaching-luoghi">
                      <div className="row g-4">
                      {/* Header con bottone Nuovo Luogo */}
                      <div className="col-12">
                        <div className="d-flex align-items-center justify-content-between mb-3">
                          <h6 className="text-uppercase text-muted small fw-semibold mb-0">
                            <i className="ri-map-pin-line me-2"></i>
                            Storico Luoghi di Allenamento
                          </h6>
                          <button
                            className="btn btn-sm btn-success"
                            onClick={() => handleOpenLocationModal()}
                          >
                            <i className="ri-add-line me-1"></i>
                            Nuovo Luogo
                          </button>
                        </div>
                      </div>

                      {/* Timeline Orizzontale Luoghi */}
                      <div className="col-12">
                        {loadingLocations ? (
                          <div className="text-center py-4">
                            <div className="spinner-border spinner-border-sm text-success" role="status"></div>
                            <small className="ms-2 text-muted">Caricamento luoghi...</small>
                          </div>
                        ) : trainingLocations.length === 0 ? (
                          <div className="card border">
                            <div className="card-body p-3 text-center text-muted">
                              <i className="ri-map-pin-line fs-3 d-block mb-2 opacity-50"></i>
                              <p className="mb-0 small">Nessun luogo configurato</p>
                              <small>Clicca "Nuovo Luogo" per aggiungerne uno</small>
                            </div>
                          </div>
                        ) : (
                          <div className="timeline-horizontal" style={{
                            overflowX: 'auto',
                            paddingBottom: '10px',
                            position: 'relative',
                          }}>
                            {/* Horizontal line */}
                            <div style={{
                              position: 'absolute',
                              left: '0',
                              right: '0',
                              top: '24px',
                              height: '3px',
                              background: 'linear-gradient(to right, #10b981, #3b82f6, #f59e0b)',
                              borderRadius: '2px',
                              zIndex: 0,
                            }}></div>

                            <div className="d-flex gap-3 align-items-start" style={{ minWidth: 'max-content', position: 'relative', zIndex: 1 }}>
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
                                    <div key={loc.id || idx} className="timeline-item-h text-center" style={{ minWidth: '140px', maxWidth: '160px' }}>
                                      {/* Dot on line */}
                                      <div className="d-flex justify-content-center mb-2">
                                        <div
                                          className="rounded-circle d-flex align-items-center justify-content-center"
                                          style={{
                                            width: '28px',
                                            height: '28px',
                                            background: bgColor,
                                            border: '3px solid #fff',
                                            boxShadow: '0 2px 8px rgba(0,0,0,0.15)',
                                          }}
                                        >
                                          <i className={`${locationIcons[loc.location]} text-white`} style={{ fontSize: '0.75rem' }}></i>
                                        </div>
                                      </div>

                                      {/* Date label */}
                                      <div className="small text-muted mb-2" style={{ fontSize: '0.7rem' }}>
                                        {loc.start_date ? new Date(loc.start_date).toLocaleDateString('it-IT') : '—'}
                                        {loc.end_date ? (
                                          <span className="d-block">→ {new Date(loc.end_date).toLocaleDateString('it-IT')}</span>
                                        ) : (
                                          <span className="d-block text-success">→ In corso</span>
                                        )}
                                      </div>

                                      {/* Card */}
                                      <div
                                        className={`card border-0 shadow-sm ${!loc.is_active ? 'opacity-75' : ''}`}
                                        style={{
                                          borderRadius: '12px',
                                          background: loc.is_active ? '#fff' : '#f8fafc',
                                          cursor: 'pointer',
                                        }}
                                        onClick={() => handleOpenLocationModal(loc)}
                                      >
                                        <div className="card-body p-2">
                                          {/* Status badge */}
                                          <div className="mb-1">
                                            {loc.is_active ? (
                                              <span className="badge bg-success" style={{ fontSize: '0.65rem' }}>Attivo</span>
                                            ) : (
                                              <span className="badge bg-secondary" style={{ fontSize: '0.65rem' }}>Concluso</span>
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
                                          <div className="fw-semibold small" style={{ fontSize: '0.8rem' }}>
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

                  {/* ===== PATOLOGIE SUB-TAB ===== */}
                  {coachingSubTab === 'patologie' && (
                    <div className="col-12" data-tour="coaching-patologie">
                      <div className="row g-4">
                      <div className="col-12">
                        <h6 className="text-uppercase text-muted small fw-semibold mb-3">
                          Patologie e Anamnesi Coaching
                        </h6>
                        <div className="card border">
                          <div className="card-body p-3">
                            <div className="d-flex align-items-center justify-content-between mb-3">
                              <div className="d-flex align-items-center">
                                <div className="rounded-circle d-flex align-items-center justify-content-center me-2" style={{ width: '28px', height: '28px', background: '#f3e8ff' }}>
                                  <i className="ri-file-list-3-line" style={{ fontSize: '0.85rem', color: '#8b5cf6' }}></i>
                                </div>
                                <span className="fw-semibold" style={{ fontSize: '0.9rem' }}>Valutazione Iniziale</span>
                              </div>
                              <button
                                className="btn btn-sm btn-primary"
                                onClick={handleSaveAnamnesiCoaching}
                                disabled={savingAnamnesiCoaching || loadingAnamnesiCoaching}
                              >
                                {savingAnamnesiCoaching ? (
                                  <><span className="spinner-border spinner-border-sm me-1"></span>Salvataggio...</>
                                ) : (
                                  <><i className="ri-save-line me-1"></i>Salva</>
                                )}
                              </button>
                            </div>
                            {loadingAnamnesiCoaching ? (
                              <div className="text-center py-4">
                                <div className="spinner-border spinner-border-sm text-primary" role="status"></div>
                                <small className="ms-2 text-muted">Caricamento anamnesi...</small>
                              </div>
                            ) : (
                              <>
                                <textarea
                                  className="form-control mb-3"
                                  rows="10"
                                  placeholder="Inserisci l'anamnesi coaching del cliente...&#10;&#10;• Esperienza sportiva&#10;• Obiettivi fitness&#10;• Infortuni pregressi&#10;• Limitazioni fisiche&#10;• Attrezzatura disponibile&#10;• Frequenza allenamenti"
                                  value={anamnesiCoachingContent}
                                  onChange={(e) => setAnamnesiCoachingContent(e.target.value)}
                                ></textarea>
                                {anamnesiCoaching && (
                                  <div className="small text-muted border-top pt-2">
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
                    <div className="col-12" data-tour="coaching-diario">
                      <div className="row g-4">
                      <div className="col-12">
                        <h6 className="text-uppercase text-muted small fw-semibold mb-3">
                          Diario Coaching
                        </h6>
                        <div className="card border">
                          <div className="card-body p-3">
                            <div className="d-flex align-items-center justify-content-between mb-3">
                              <div className="d-flex align-items-center">
                                <div className="rounded-circle d-flex align-items-center justify-content-center me-2" style={{ width: '28px', height: '28px', background: '#fce7f3' }}>
                                  <i className="ri-book-2-line" style={{ fontSize: '0.85rem', color: '#ec4899' }}></i>
                                </div>
                                <span className="fw-semibold" style={{ fontSize: '0.9rem' }}>Note del Percorso</span>
                                <span className="badge bg-secondary ms-2">{diarioCoachingEntries.length}</span>
                              </div>
                              <button
                                className="btn btn-sm btn-primary"
                                onClick={() => handleOpenDiarioCoachingModal()}
                              >
                                <i className="ri-add-line me-1"></i>
                                Nuova Nota
                              </button>
                            </div>
                            {loadingDiarioCoaching ? (
                              <div className="text-center py-4">
                                <div className="spinner-border spinner-border-sm text-primary" role="status"></div>
                                <small className="ms-2 text-muted">Caricamento diario...</small>
                              </div>
                            ) : diarioCoachingEntries.length === 0 ? (
                              <p className="text-muted small mb-0 text-center py-3">
                                <i className="ri-information-line me-1"></i>
                                Nessuna nota nel diario. Clicca "Nuova Nota" per aggiungerne una.
                              </p>
                            ) : (
                              <div className="d-flex flex-column gap-3">
                                {diarioCoachingEntries.map((entry) => (
                                  <div key={entry.id} className="border rounded-3 p-3" style={{ background: '#fafafa' }}>
                                    <div className="d-flex justify-content-between align-items-start mb-2">
                                      <div>
                                        <span className="badge bg-warning-subtle text-warning me-2">
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
                                      <div className="d-flex gap-1">
                                        <button
                                          className="btn btn-sm btn-outline-primary py-0 px-2"
                                          onClick={() => handleOpenDiarioCoachingModal(entry)}
                                          title="Modifica"
                                        >
                                          <i className="ri-edit-line"></i>
                                        </button>
                                        {(user?.is_admin || user?.role === 'admin') && (
                                          <button
                                            className="btn btn-sm btn-outline-danger py-0 px-2"
                                            onClick={() => handleDeleteDiarioCoaching(entry.id)}
                                            title="Elimina"
                                          >
                                            <i className="ri-delete-bin-line"></i>
                                          </button>
                                        )}
                                        <button
                                          className="btn btn-sm btn-outline-secondary py-0 px-2"
                                          onClick={() => handleOpenHistoryModal(entry, 'coaching')}
                                          title="Storico Modifiche"
                                        >
                                          <i className="ri-history-line"></i>
                                        </button>
                                      </div>
                                    </div>
                                    <p className="mb-0 small" style={{ whiteSpace: 'pre-wrap' }}>{entry.content}</p>
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
                    <div className="col-12" data-tour="coaching-alert">
                      <div className="row g-4">
                      <div className="col-12">
                        <h6 className="text-uppercase text-muted small fw-semibold mb-3">
                          Alert e Criticità
                        </h6>
                        <div className="card border border-danger">
                          <div className="card-body p-3">
                            <div className="d-flex align-items-center mb-3">
                              <div className="bg-danger-subtle rounded-circle d-flex align-items-center justify-content-center me-2" style={{ width: '28px', height: '28px' }}>
                                <i className="ri-alarm-warning-line text-danger" style={{ fontSize: '0.85rem' }}></i>
                              </div>
                              <span className="fw-semibold text-danger" style={{ fontSize: '0.9rem' }}>Alert Coaching</span>
                            </div>
                            <p className="text-muted small mb-2">
                              Informazioni critiche: infortuni, limitazioni fisiche, controindicazioni.
                              Queste note saranno sempre visibili in evidenza.
                            </p>
                            <textarea
                              className="form-control border-danger"
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
                  )}
                </div>
              )}

              {/* ========== PSICOLOGIA TAB ========== */}
              {activeTab === 'psicologia' && (
                <div className="row g-4">
                  {/* Alert Psicologia - show at top if present */}
                  {formData.alert_psicologia && (
                    <div className="col-12">
                      <div className="alert alert-danger border-danger mb-0 d-flex align-items-start">
                        <i className="ri-alarm-warning-line fs-4 me-2 text-danger"></i>
                        <div>
                          <strong className="small">Alert Psicologia</strong>
                          <p className="mb-0 small">{formData.alert_psicologia}</p>
                        </div>
                      </div>
                    </div>
                  )}

                  {/* Sub-tab Navigation - Same style as Nutrizione/Coaching */}
                  <div className="col-12" data-tour="psicologia-subtabs">
                    <div style={{ overflowX: 'auto', overflowY: 'hidden', WebkitOverflowScrolling: 'touch', scrollbarWidth: 'none', msOverflowStyle: 'none' }}>
                      <ul className="nav nav-pills mb-0" style={{ gap: '8px', flexWrap: 'nowrap', minWidth: 'max-content' }}>
                        {[
                          { key: 'panoramica', label: 'Panoramica', icon: 'ri-dashboard-line', color: '#a855f7' },
                          { key: 'setup', label: 'Setup', icon: 'ri-settings-3-line', color: '#3b82f6' },
                          { key: 'patologie', label: 'Patologie', icon: 'ri-stethoscope-line', color: '#f59e0b' },
                          { key: 'diario', label: 'Diario', icon: 'ri-book-2-line', color: '#ec4899' },
                          { key: 'alert', label: 'Alert', icon: 'ri-alarm-warning-line', color: '#ef4444' },
                        ].map(({ key, label, icon, color }) => (
                          <li key={key} className="nav-item">
                            <button
                              className="nav-link"
                              onClick={() => setPsicologiaSubTab(key)}
                              style={{
                                background: psicologiaSubTab === key ? `linear-gradient(135deg, ${color} 0%, ${color}dd 100%)` : '#f1f5f9',
                                color: psicologiaSubTab === key ? '#fff' : '#64748b',
                                border: 'none',
                                borderRadius: '8px',
                                padding: '8px 16px',
                                fontWeight: 600,
                                fontSize: '0.85rem',
                                whiteSpace: 'nowrap',
                              }}
                            >
                              <i className={`${icon} me-1`}></i>
                              {label}
                            </button>
                          </li>
                        ))}
                      </ul>
                    </div>
                  </div>

                  {/* ===== PANORAMICA SUB-TAB ===== */}
                  {psicologiaSubTab === 'panoramica' && (
                    <div className="col-12" data-tour="psicologia-panoramica">
                      <div className="row g-4">
                      {/* Psicologi Assegnati */}
                      <div className="col-12">
                        <h6 className="text-uppercase text-muted small fw-semibold mb-3">
                          Psicologi Assegnati
                        </h6>
                        {loadingHistory ? (
                          <div className="text-center py-4">
                            <div className="spinner-border spinner-border-sm text-purple" role="status"></div>
                            <small className="ms-2 text-muted">Caricamento...</small>
                          </div>
                        ) : (
                          <div className="card border">
                            <div className="card-body p-3">
                              <div className="d-flex align-items-center justify-content-between mb-3">
                                <div className="d-flex align-items-center">
                                  <div className="rounded-circle d-flex align-items-center justify-content-center me-2"
                                       style={{ width: '32px', height: '32px', background: '#f3e8ff' }}>
                                    <i className="ri-mental-health-line" style={{ color: '#a855f7' }}></i>
                                  </div>
                                  <span className="fw-semibold">Team Psicologia</span>
                                </div>
                                <span className="badge" style={{ background: '#a855f7' }}>{getActiveProfessionals('psicologa').length} attivi</span>
                              </div>

                              {getActiveProfessionals('psicologa').length > 0 ? (
                                <div className="d-flex flex-wrap gap-2">
                                  {getActiveProfessionals('psicologa').map((assignment, idx) => (
                                    <div key={idx} className="d-flex align-items-center p-2 bg-light rounded">
                                      {assignment.avatar_path ? (
                                        <img src={assignment.avatar_path} alt="" className="rounded-circle me-2" style={{ width: '32px', height: '32px', objectFit: 'cover' }} />
                                      ) : (
                                        <div className="rounded-circle text-white d-flex align-items-center justify-content-center me-2" style={{ width: '32px', height: '32px', fontSize: '0.75rem', background: '#a855f7' }}>
                                          {assignment.professionista_nome?.split(' ').map(n => n[0]).join('').substring(0,2).toUpperCase() || '??'}
                                        </div>
                                      )}
                                      <div>
                                        <small className="d-block fw-medium">{assignment.professionista_nome}</small>
                                        <small className="text-muted" style={{ fontSize: '0.7rem' }}>dal {assignment.data_dal}</small>
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
                        <div className="col-12">
                          <h6 className="text-uppercase text-muted small fw-semibold mb-3">
                            <i className="ri-history-line me-2"></i>
                            Storico Assegnazioni
                          </h6>
                          <div className="timeline-horizontal" style={{ overflowX: 'auto', paddingBottom: '10px', position: 'relative' }}>
                            <div style={{ position: 'absolute', left: '0', right: '0', top: '24px', height: '3px', background: 'linear-gradient(to right, #a855f7, #7c3aed)', borderRadius: '2px', zIndex: 0 }}></div>
                            <div className="d-flex gap-3 align-items-start" style={{ minWidth: 'max-content', position: 'relative', zIndex: 1 }}>
                              {professionistiHistory
                                .filter(h => h.tipo_professionista === 'psicologa')
                                .sort((a, b) => {
                                  const dateA = new Date(a.data_dal?.split('/').reverse().join('-') || 0);
                                  const dateB = new Date(b.data_dal?.split('/').reverse().join('-') || 0);
                                  return dateB - dateA;
                                })
                                .map((item, idx) => (
                                  <div key={idx} className="timeline-item-h text-center" style={{ minWidth: '140px', maxWidth: '160px' }}>
                                    <div className="d-flex justify-content-center mb-2">
                                      <div className="rounded-circle d-flex align-items-center justify-content-center" style={{ width: '28px', height: '28px', background: '#a855f7', border: '3px solid #fff', boxShadow: '0 2px 8px rgba(0,0,0,0.15)' }}>
                                        <i className="ri-mental-health-line text-white" style={{ fontSize: '0.75rem' }}></i>
                                      </div>
                                    </div>
                                    <div className="small text-muted mb-2" style={{ fontSize: '0.7rem' }}>
                                      {item.data_dal || '—'}
                                      {item.data_al && <span className="d-block">→ {item.data_al}</span>}
                                    </div>
                                    <div className={`card border-0 shadow-sm ${!item.is_active ? 'opacity-75' : ''}`} style={{ borderRadius: '12px', background: item.is_active ? '#fff' : '#f8fafc' }}>
                                      <div className="card-body p-2">
                                        <div className="mb-2">
                                          {item.is_active ? (
                                            <span className="badge" style={{ fontSize: '0.65rem', background: '#a855f7' }}>Attivo</span>
                                          ) : (
                                            <span className="badge bg-secondary" style={{ fontSize: '0.65rem' }}>Concluso</span>
                                          )}
                                        </div>
                                        <div className="d-flex justify-content-center mb-2">
                                          {item.avatar_path ? (
                                            <img src={item.avatar_path} alt="" className="rounded-circle" style={{ width: '36px', height: '36px', objectFit: 'cover' }} />
                                          ) : (
                                            <div className="rounded-circle text-white d-flex align-items-center justify-content-center" style={{ width: '36px', height: '36px', fontSize: '0.75rem', background: '#a855f7' }}>
                                              {item.professionista_nome?.split(' ').map(n => n[0]).join('').substring(0,2).toUpperCase() || '??'}
                                            </div>
                                          )}
                                        </div>
                                        <div className="fw-semibold small" style={{ fontSize: '0.8rem', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
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
                      <div className="col-md-6">
                        <h6 className="text-uppercase text-muted small fw-semibold mb-3">Stato Servizio</h6>
                        <div className="card border">
                          <div className="card-body p-3">
                            <div className="d-flex align-items-center mb-3">
                              <div className="rounded-circle d-flex align-items-center justify-content-center me-2" style={{ width: '28px', height: '28px', background: '#f3e8ff' }}>
                                <i className="ri-mental-health-line" style={{ fontSize: '0.85rem', color: '#a855f7' }}></i>
                              </div>
                              <span className="fw-semibold" style={{ fontSize: '0.9rem' }}>Stato Psicologia</span>
                            </div>
                            <select
                              className="form-select form-select-sm mb-2"
                              value={formData.stato_psicologia || ''}
                              onChange={(e) => handleInputChange('stato_psicologia', e.target.value)}
                            >
                              <option value="">Seleziona stato...</option>
                              <option value="attivo">Attivo</option>
                              <option value="pausa">Pausa</option>
                              <option value="ghost">Ghost</option>
                              <option value="stop">Ex-Cliente</option>
                            </select>
                            {c.stato_psicologia_data && (
                              <small className="text-muted" style={{ fontSize: '0.7rem' }}>
                                <i className="ri-calendar-line me-1"></i>
                                Ultimo cambio: {new Date(c.stato_psicologia_data).toLocaleDateString('it-IT')}
                              </small>
                            )}
                          </div>
                        </div>
                      </div>

                      <div className="col-md-6">
                        <h6 className="text-uppercase text-muted small fw-semibold mb-3">Stato Chat</h6>
                        <div className="card border">
                          <div className="card-body p-3">
                            <div className="d-flex align-items-center mb-3">
                              <div className="bg-secondary-subtle rounded-circle d-flex align-items-center justify-content-center me-2" style={{ width: '28px', height: '28px' }}>
                                <i className="ri-chat-3-line text-secondary" style={{ fontSize: '0.85rem' }}></i>
                              </div>
                              <span className="fw-semibold" style={{ fontSize: '0.9rem' }}>Stato Chat Psicologia</span>
                            </div>
                            <select
                              className="form-select form-select-sm mb-2"
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

                      {/* Timeline Storico Stati Unificata */}
                      <div className="col-12">
                        <h6 className="text-uppercase text-muted small fw-semibold mb-3">
                          <i className="ri-history-line me-2"></i>
                          Storico Stati (Servizio + Chat)
                        </h6>
                        {loadingStoricoPsicologia ? (
                          <div className="text-center py-4">
                            <div className="spinner-border spinner-border-sm" style={{ color: '#a855f7' }} role="status"></div>
                            <small className="ms-2 text-muted">Caricamento storico...</small>
                          </div>
                        ) : (storicoStatoPsicologia.length > 0 || storicoChatPsicologia.length > 0) ? (
                          <div className="timeline-horizontal" style={{ overflowX: 'auto', paddingBottom: '10px', position: 'relative' }}>
                            <div style={{ position: 'absolute', left: '0', right: '0', top: '24px', height: '3px', background: 'linear-gradient(to right, #a855f7, #6b7280)', borderRadius: '2px', zIndex: 0 }}></div>
                            <div className="d-flex gap-3 align-items-start" style={{ minWidth: 'max-content', position: 'relative', zIndex: 1 }}>
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
                                    <div key={idx} className="timeline-item-h text-center" style={{ minWidth: '130px', maxWidth: '150px' }}>
                                      <div className="d-flex justify-content-center mb-2">
                                        <div className="rounded-circle d-flex align-items-center justify-content-center" style={{ width: '28px', height: '28px', background: bgColor, border: '3px solid #fff', boxShadow: '0 2px 8px rgba(0,0,0,0.15)' }}>
                                          <i className={`${icon} text-white`} style={{ fontSize: '0.75rem' }}></i>
                                        </div>
                                      </div>
                                      <div className="small text-muted mb-2" style={{ fontSize: '0.7rem' }}>
                                        {item.data_inizio || '—'}
                                        {item.data_fine && <span className="d-block">→ {item.data_fine}</span>}
                                      </div>
                                      <div className={`card border-0 shadow-sm ${!item.is_attivo ? 'opacity-75' : ''}`} style={{ borderRadius: '12px', background: item.is_attivo ? '#fff' : '#f8fafc' }}>
                                        <div className="card-body p-2">
                                          <div className="mb-1">
                                            <span className="badge" style={{ fontSize: '0.6rem', background: isServizio ? '#f3e8ff' : '#f3f4f6', color: bgColor }}>
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
                          <div className="card border">
                            <div className="card-body p-3 text-center text-muted">
                              <i className="ri-history-line fs-3 d-block mb-2 opacity-50"></i>
                              <p className="mb-0 small">Nessuno storico stati disponibile</p>
                              <small>I cambi di stato verranno tracciati automaticamente</small>
                            </div>
                          </div>
                        )}
                      </div>
                      </div>
                    </div>
                  )}

                  {/* ===== SETUP SUB-TAB ===== */}
                  {psicologiaSubTab === 'setup' && (
                    <div className="col-12" data-tour="psicologia-setup">
                      <div className="row g-4">
                      {/* Call Iniziale */}
                      <div className="col-12">
                        <h6 className="text-uppercase text-muted small fw-semibold mb-3">Call Iniziale</h6>
                        <div className="card border">
                          <div className="card-body p-3">
                            <div className="d-flex align-items-center mb-3">
                              <div className="bg-primary-subtle rounded-circle d-flex align-items-center justify-content-center me-2" style={{ width: '28px', height: '28px' }}>
                                <i className="ri-phone-line text-primary" style={{ fontSize: '0.85rem' }}></i>
                              </div>
                              <span className="fw-semibold" style={{ fontSize: '0.9rem' }}>Call Iniziale Psicologa</span>
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
                                <span className="badge bg-success ms-2" style={{ fontSize: '0.65rem' }}>Completata</span>
                              )}
                            </div>
                            {formData.call_iniziale_psicologa && (
                              <div className="mt-3">
                                <label className="form-label small text-muted mb-1">Data Call</label>
                                <input
                                  type="date"
                                  className="form-control form-control-sm"
                                  value={formData.data_call_iniziale_psicologia || ''}
                                  onChange={(e) => handleInputChange('data_call_iniziale_psicologia', e.target.value)}
                                />
                              </div>
                            )}
                          </div>
                        </div>
                      </div>

                      {/* Reach Out */}
                      <div className="col-12">
                        <h6 className="text-uppercase text-muted small fw-semibold mb-3">Reach Out Settimanale</h6>
                        <div className="card border">
                          <div className="card-body p-3">
                            <div className="d-flex align-items-center mb-3">
                              <div className="bg-info-subtle rounded-circle d-flex align-items-center justify-content-center me-2" style={{ width: '28px', height: '28px' }}>
                                <i className="ri-calendar-check-line text-info" style={{ fontSize: '0.85rem' }}></i>
                              </div>
                              <span className="fw-semibold" style={{ fontSize: '0.9rem' }}>Giorno Reach Out</span>
                            </div>
                            <select
                              className="form-select form-select-sm"
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
                            {formData.reach_out_psicologia && (
                              <small className="text-muted d-block mt-2" style={{ fontSize: '0.7rem' }}>
                                <i className="ri-calendar-event-line me-1"></i>
                                Reach out ogni {{ lunedi: 'Lunedì', martedi: 'Martedì', mercoledi: 'Mercoledì', giovedi: 'Giovedì', venerdi: 'Venerdì', sabato: 'Sabato', domenica: 'Domenica' }[formData.reach_out_psicologia]}
                              </small>
                            )}
                          </div>
                        </div>
                      </div>

                      {/* Sedute Counter */}
                      <div className="col-md-6">
                        <h6 className="text-uppercase text-muted small fw-semibold mb-3">Sedute Acquistate</h6>
                        <div className="card border">
                          <div className="card-body p-3">
                            <div className="d-flex align-items-center justify-content-between">
                              <div className="d-flex align-items-center">
                                <div className="rounded-circle d-flex align-items-center justify-content-center me-2" style={{ width: '40px', height: '40px', background: '#dbeafe' }}>
                                  <i className="ri-shopping-cart-line text-primary" style={{ fontSize: '1rem' }}></i>
                                </div>
                                <span className="fw-semibold">Sedute Comprate</span>
                              </div>
                              <input
                                type="number"
                                className="form-control form-control-sm text-center"
                                style={{ width: '80px' }}
                                min="0"
                                value={formData.sedute_psicologia_comprate || 0}
                                onChange={(e) => handleInputChange('sedute_psicologia_comprate', parseInt(e.target.value) || 0)}
                              />
                            </div>
                          </div>
                        </div>
                      </div>

                      <div className="col-md-6">
                        <h6 className="text-uppercase text-muted small fw-semibold mb-3">Sedute Svolte</h6>
                        <div className="card border">
                          <div className="card-body p-3">
                            <div className="d-flex align-items-center justify-content-between">
                              <div className="d-flex align-items-center">
                                <div className="rounded-circle d-flex align-items-center justify-content-center me-2" style={{ width: '40px', height: '40px', background: '#d1fae5' }}>
                                  <i className="ri-check-double-line text-success" style={{ fontSize: '1rem' }}></i>
                                </div>
                                <span className="fw-semibold">Sedute Svolte</span>
                              </div>
                              <input
                                type="number"
                                className="form-control form-control-sm text-center"
                                style={{ width: '80px' }}
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
                    <div className="col-12" data-tour="psicologia-patologie">
                      <div className="row g-4">
                      <div className="col-12">
                        <h6 className="text-uppercase text-muted small fw-semibold mb-3">Patologie Psicologiche</h6>
                        <div className="card border">
                          <div className="card-body p-3">
                            <div className="d-flex align-items-center mb-3">
                              <div className="rounded-circle d-flex align-items-center justify-content-center me-2" style={{ width: '28px', height: '28px', background: '#fef3c7' }}>
                                <i className="ri-stethoscope-line text-warning" style={{ fontSize: '0.85rem' }}></i>
                              </div>
                              <span className="fw-semibold" style={{ fontSize: '0.9rem' }}>Patologie Psicologiche</span>
                            </div>

                            {/* Nessuna Patologia */}
                            <div className={`p-2 rounded mb-3 border ${formData.nessuna_patologia_psico ? 'bg-success-subtle border-success' : 'border-secondary'}`}>
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
                            <div className="row g-1">
                              {PATOLOGIE_PSICO.map(({ key, label }) => (
                                <div key={key} className="col-md-6 col-12">
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
                              <div className="col-md-6 col-12">
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
                              <div className="mt-2">
                                <input
                                  type="text"
                                  className="form-control form-control-sm"
                                  placeholder="Specifica altra patologia psicologica..."
                                  value={formData.patologia_psico_altro || ''}
                                  onChange={(e) => handleInputChange('patologia_psico_altro', e.target.value)}
                                />
                              </div>
                            )}
                          </div>
                        </div>
                      </div>

                      {/* ===== ANAMNESI MERGED ===== */}
                      <div className="col-12">
                        <h6 className="text-uppercase text-muted small fw-semibold mb-3">Storia Psicologica</h6>
                        <div className="card border">
                          <div className="card-body p-3">
                            <div className="d-flex align-items-center mb-3">
                              <div className="rounded-circle d-flex align-items-center justify-content-center me-2" style={{ width: '28px', height: '28px', background: '#f3e8ff' }}>
                                <i className="ri-file-list-3-line" style={{ fontSize: '0.85rem', color: '#a855f7' }}></i>
                              </div>
                              <span className="fw-semibold" style={{ fontSize: '0.9rem' }}>Anamnesi Psicologica</span>
                            </div>
                            <textarea
                              className="form-control mb-3"
                              rows="8"
                              placeholder="Scrivi qui l'anamnesi psicologica del cliente...&#10;&#10;• Storia clinica&#10;• Motivazioni&#10;• Obiettivi terapeutici&#10;• Note iniziali"
                              value={formData.storia_psicologica || ''}
                              onChange={(e) => handleInputChange('storia_psicologica', e.target.value)}
                            ></textarea>
                          </div>
                        </div>
                      </div>
                      </div>
                    </div>
                  )}



                  {/* ===== DIARIO SUB-TAB ===== */}
                  {psicologiaSubTab === 'diario' && (
                    <div className="col-12" data-tour="psicologia-diario">
                      <div className="row g-4">
                      <div className="col-12">
                        <h6 className="text-uppercase text-muted small fw-semibold mb-3">
                          Diario Psicologia
                        </h6>
                        <div className="card border">
                          <div className="card-body p-3">
                            <div className="d-flex align-items-center justify-content-between mb-3">
                              <div className="d-flex align-items-center">
                                <div className="rounded-circle d-flex align-items-center justify-content-center me-2" style={{ width: '28px', height: '28px', background: '#f3e8ff' }}>
                                  <i className="ri-book-2-line" style={{ fontSize: '0.85rem', color: '#a855f7' }}></i>
                                </div>
                                <span className="fw-semibold" style={{ fontSize: '0.9rem' }}>Note del Percorso</span>
                                <span className="badge ms-2" style={{ background: '#a855f7' }}>{diarioPsicologiaEntries.length}</span>
                              </div>
                              <button
                                className="btn btn-sm"
                                style={{ background: '#a855f7', color: 'white' }}
                                onClick={() => handleOpenDiarioPsicologiaModal()}
                              >
                                <i className="ri-add-line me-1"></i>
                                Nuova Nota
                              </button>
                            </div>

                            {loadingDiarioPsicologia ? (
                              <div className="text-center py-4">
                                <div className="spinner-border spinner-border-sm" style={{ color: '#a855f7' }} role="status"></div>
                                <small className="ms-2 text-muted">Caricamento diario...</small>
                              </div>
                            ) : diarioPsicologiaEntries.length === 0 ? (
                              <p className="text-muted small mb-0 text-center py-3">
                                <i className="ri-information-line me-1"></i>
                                Nessuna nota nel diario. Clicca "Nuova Nota" per aggiungerne una.
                              </p>
                            ) : (
                              <div className="d-flex flex-column gap-3">
                                {diarioPsicologiaEntries.map((entry) => (
                                  <div key={entry.id} className="border rounded-3 p-3" style={{ background: '#fafafa' }}>
                                    <div className="d-flex justify-content-between align-items-start mb-2">
                                      <div>
                                        <span className="badge me-2" style={{ background: '#f3e8ff', color: '#a855f7' }}>
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
                                      <div className="d-flex gap-1">
                                        <button
                                          className="btn btn-sm btn-outline-primary py-0 px-2"
                                          onClick={() => handleOpenDiarioPsicologiaModal(entry)}
                                          title="Modifica"
                                        >
                                          <i className="ri-edit-line"></i>
                                        </button>
                                        {(user?.is_admin || user?.role === 'admin') && (
                                          <button
                                            className="btn btn-sm btn-outline-danger py-0 px-2"
                                            onClick={() => handleDeleteDiarioPsicologia(entry.id)}
                                            title="Elimina"
                                          >
                                            <i className="ri-delete-bin-line"></i>
                                          </button>
                                        )}
                                        <button
                                          className="btn btn-sm btn-outline-secondary py-0 px-2"
                                          onClick={() => handleOpenHistoryModal(entry, 'psicologia')}
                                          title="Storico Modifiche"
                                        >
                                          <i className="ri-history-line"></i>
                                        </button>
                                      </div>
                                    </div>
                                    <p className="mb-0 small" style={{ whiteSpace: 'pre-wrap' }}>{entry.content}</p>
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
                    <div className="col-12" data-tour="psicologia-alert">
                      <div className="row g-4">
                      <div className="col-12">
                        <h6 className="text-uppercase text-muted small fw-semibold mb-3">Alert / Criticità</h6>
                        <div className="card border border-danger">
                          <div className="card-body p-3">
                            <div className="d-flex align-items-center mb-3">
                              <div className="bg-danger-subtle rounded-circle d-flex align-items-center justify-content-center me-2" style={{ width: '28px', height: '28px' }}>
                                <i className="ri-alarm-warning-line text-danger" style={{ fontSize: '0.85rem' }}></i>
                              </div>
                              <span className="fw-semibold" style={{ fontSize: '0.9rem' }}>Note Critiche Psicologia</span>
                            </div>
                            <textarea
                              className="form-control"
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
                  )}
                </div>
              )}

              {/* ========== CHECK TAB ========== */}
              {/* ========== CHECK PERIODICI TAB ========== */}
              {activeTab === 'check_periodici' && (
                <div className="row g-4">
                  {/* Pills Navigation */}
                  <div className="col-12" data-tour="check-periodici-tabs">
                    <ul className="nav nav-pills mb-3">
                      <li className="nav-item">
                        <button 
                          className={`nav-link ${activePeriodiciTab === 'weekly' ? 'active' : ''}`} 
                          onClick={() => setActivePeriodiciTab('weekly')}
                        >
                          Settimanale
                        </button>
                      </li>
                      <li className="nav-item">
                        <button 
                          className={`nav-link ${activePeriodiciTab === 'dca' ? 'active' : ''}`} 
                          onClick={() => setActivePeriodiciTab('dca')}
                        >
                          DCA
                        </button>
                      </li>
                      <li className="nav-item">
                        <button 
                          className={`nav-link ${activePeriodiciTab === 'minor' ? 'active' : ''}`} 
                          onClick={() => setActivePeriodiciTab('minor')}
                        >
                          Minori
                        </button>
                      </li>
                    </ul>
                  </div>

                  {/* Link Generation Section (Filtered) */}
                  <div className="col-12" data-tour="check-periodici-link">
                    <h6 className="text-uppercase text-muted small fw-semibold mb-3">
                      <i className="ri-link me-2"></i>
                      Genera Link Check
                    </h6>
                    <div className="row g-3">
                      {Object.values(CHECK_TYPES)
                        .filter(t => t.key === activePeriodiciTab)
                        .map((checkType) => {
                        const existingCheck = checkData.checks[checkType.key];
                        return (
                          <div key={checkType.key} className="col-md-6 col-lg-4">
                            <div className="card border">
                              <div className="card-body p-3">
                                <div className="d-flex align-items-center">
                                  <div className="rounded-circle d-flex align-items-center justify-content-center me-2"
                                       style={{ width: '32px', height: '32px', background: checkType.bgColor }}>
                                    <i className={checkType.icon} style={{ color: checkType.color, fontSize: '14px' }}></i>
                                  </div>
                                  <div>
                                    <span className="fw-semibold d-block" style={{ fontSize: '0.85rem' }}>{checkType.label}</span>
                                    {existingCheck && (
                                      <small className="text-muted" style={{ fontSize: '0.7rem' }}>
                                        {existingCheck.response_count} compilazioni
                                      </small>
                                    )}
                                  </div>
                                </div>
                                <div className="d-flex gap-2 mt-4">
                                  <button
                                    className="btn btn-sm flex-grow-1"
                                    style={{ background: checkType.color, color: 'white', fontSize: '0.75rem' }}
                                    onClick={() => handleGenerateCheckLink(checkType.key)}
                                    disabled={generatingLink === checkType.key}
                                  >
                                    {generatingLink === checkType.key ? (
                                      <span className="spinner-border spinner-border-sm me-1"></span>
                                    ) : (
                                      <i className={existingCheck ? 'ri-file-copy-line me-1' : 'ri-add-line me-1'}></i>
                                    )}
                                    {existingCheck ? 'Copia Link' : 'Genera Link'}
                                  </button>
                                  {existingCheck && (
                                    <button
                                      className="btn btn-sm btn-outline-secondary"
                                      onClick={() => handleOpenCheckForm(existingCheck.url)}
                                      title="Apri form"
                                      style={{ fontSize: '0.75rem' }}
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
                  </div>

                  {/* Responses History Section (Filtered) */}
                  <div className="col-12" data-tour="check-periodici-risposte">
                    <h6 className="text-uppercase text-muted small fw-semibold mb-3">
                      <i className="ri-history-line me-2"></i>
                      Storico Compilazioni
                    </h6>
                    <div className="card border">
                      <div className="card-body p-3">
                        {loadingChecks ? (
                          <div className="text-center py-4">
                            <div className="spinner-border spinner-border-sm text-primary" role="status"></div>
                            <small className="ms-2 text-muted">Caricamento check...</small>
                          </div>
                        ) : checkData.responses.filter(r => r.type === activePeriodiciTab).length === 0 ? (
                          <div className="text-center py-4">
                            <i className="ri-inbox-line fs-2 text-muted d-block mb-2"></i>
                            <p className="text-muted small mb-0">Nessuna compilazione ricevuta</p>
                          </div>
                        ) : (
                          <div className="table-responsive">
                            <table className="table table-hover mb-0">
                              <thead>
                                <tr>
                                  <th style={{ fontSize: '0.75rem' }}>Data</th>
                                  <th style={{ fontSize: '0.75rem' }}>Tipo</th>
                                  <th style={{ fontSize: '0.75rem' }} className="text-center">Valutazioni</th>
                                  <th style={{ fontSize: '0.75rem' }} className="text-center">Azioni</th>
                                </tr>
                              </thead>
                              <tbody>
                                {checkData.responses
                                  .filter(r => r.type === activePeriodiciTab)
                                  .map((response) => (
                                  <tr key={`${response.type}-${response.id}`}>
                                    <td>
                                      <small className="fw-medium">{response.submit_date}</small>
                                    </td>
                                    <td>
                                      <span className="badge" style={{
                                        background: CHECK_TYPES[response.type]?.bgColor || '#f1f5f9',
                                        color: CHECK_TYPES[response.type]?.color || '#64748b',
                                        fontSize: '0.7rem'
                                      }}>
                                        <i className={`${CHECK_TYPES[response.type]?.icon} me-1`}></i>
                                        {CHECK_TYPES[response.type]?.label || response.type}
                                      </span>
                                    </td>
                                    <td className="text-center">
                                      {response.type === 'weekly' && (
                                        <div className="d-flex justify-content-center gap-2">
                                          {response.nutritionist_rating && (
                                            <span style={checkService.getRatingBadgeStyle(response.nutritionist_rating)} title="Nutrizionista">
                                              🥗 {response.nutritionist_rating}
                                            </span>
                                          )}
                                          {response.psychologist_rating && (
                                            <span style={checkService.getRatingBadgeStyle(response.psychologist_rating)} title="Psicologo">
                                              🧠 {response.psychologist_rating}
                                            </span>
                                          )}
                                          {response.coach_rating && (
                                            <span style={checkService.getRatingBadgeStyle(response.coach_rating)} title="Coach">
                                              🏋️ {response.coach_rating}
                                            </span>
                                          )}
                                          {response.progress_rating && (
                                            <span style={checkService.getRatingBadgeStyle(response.progress_rating)} title="Progresso">
                                              📈 {response.progress_rating}
                                            </span>
                                          )}
                                        </div>
                                      )}
                                      {response.type === 'minor' && response.score_global && (
                                        <span style={checkService.getRatingBadgeStyle(10 - response.score_global)}>
                                          EDE-Q6: {response.score_global.toFixed(1)}
                                        </span>
                                      )}
                                      {response.type === 'dca' && (
                                        <small className="text-muted">-</small>
                                      )}
                                    </td>
                                    <td className="text-center">
                                      <button
                                        className="btn btn-sm btn-outline-primary py-0 px-2"
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
                </div>
              )}

              {/* ========== CHECK INIZIALI TAB ========== */}
              {activeTab === 'check_iniziali' && (
                 <div className="row g-4">
                    {/* Pills Navigation */}
                    <div className="col-12" data-tour="check-iniziali-tabs">
                       <ul className="nav nav-pills mb-3">
                          <li className="nav-item">
                             <button className={`nav-link ${activeInizialiTab === 'check_1' ? 'active' : ''}`} onClick={() => setActiveInizialiTab('check_1')}>Check 1</button>
                          </li>
                          <li className="nav-item">
                             <button className={`nav-link ${activeInizialiTab === 'check_2' ? 'active' : ''}`} onClick={() => setActiveInizialiTab('check_2')}>Check 2</button>
                          </li>
                       </ul>
                    </div>
                    
                    {/* Content */}
                     <div className="col-12" data-tour="check-iniziali-contenuto">
                       <div className="card border">
                          <div className="card-body p-4">
                             {loadingInitialChecks ? (
                                <div className="text-center py-5">
                                   <div className="spinner-border text-primary" role="status"></div>
                                   <p className="mt-2 text-muted">Caricamento risposte...</p>
                                </div>
                             ) : !initialChecksData || !initialChecksData[activeInizialiTab] ? (
                                <div className="text-center py-5">
                                   <i className="ri-file-search-line fs-1 text-muted mb-3"></i>
                                   <h5>Nessun dato disponibile</h5>
                                   <p className="text-muted">Il {activeInizialiTab.replace('_', ' ')} non è disponibile per questo cliente.</p>
                                </div>
                             ) : (() => {
                                const checkData = initialChecksData[activeInizialiTab];
                                const hasResponses = checkData.responses && Object.keys(checkData.responses).length > 0;
                                const hasUrl = checkData.url;
                                if (!hasResponses && hasUrl) {
                                  return (
                                    <div>
                                      <div className="d-flex justify-content-between align-items-center mb-4 border-bottom pb-3">
                                        <h5 className="mb-0 text-capitalize">{activeInizialiTab.replace('_', ' ')}</h5>
                                      </div>
                                      <div className="alert alert-info d-flex align-items-center">
                                        <i className="ri-link fs-4 me-3"></i>
                                        <div className="flex-grow-1">
                                          <strong>Link da inviare al cliente</strong>
                                          <p className="mb-2 mt-1 text-muted small">Il cliente non ha ancora compilato. Copia il link qui sotto e invialo al cliente per permettergli di compilare il questionario.</p>
                                          <div className="input-group">
                                            <input type="text" className="form-control" value={checkData.url} readOnly />
                                            <button className="btn btn-primary" type="button" onClick={() => { navigator.clipboard.writeText(checkData.url); alert('Link copiato negli appunti'); }}>
                                              <i className="ri-file-copy-line me-1"></i>Copia
                                            </button>
                                          </div>
                                        </div>
                                      </div>
                                    </div>
                                  );
                                }
                                if (!hasResponses && !hasUrl) {
                                  return (
                                    <div className="text-center py-5">
                                      <i className="ri-file-search-line fs-1 text-muted mb-3"></i>
                                      <h5>Nessun dato disponibile</h5>
                                      <p className="text-muted">Il {activeInizialiTab.replace('_', ' ')} non è stato ancora compilato o non è disponibile per questo cliente.</p>
                                    </div>
                                  );
                                }
                                return (
                                <div>
                                   <div className="d-flex justify-content-between align-items-center mb-4 border-bottom pb-3">
                                      <h5 className="mb-0 text-capitalize">{activeInizialiTab.replace('_', ' ')}</h5>
                                      {checkData.completed_at && (
                                         <span className="badge bg-light text-dark border">
                                            <i className="ri-calendar-event-line me-1"></i>
                                            Compilato il: {new Date(checkData.completed_at).toLocaleDateString('it-IT')}
                                         </span>
                                      )}
                                      {hasUrl && (
                                         <button className="btn btn-sm btn-outline-primary ms-2" onClick={() => { navigator.clipboard.writeText(checkData.url); alert('Link copiato'); }}>
                                            <i className="ri-file-copy-line me-1"></i>Copia link
                                         </button>
                                      )}
                                   </div>
                                   
                                   {/* Responses List */}
                                   <div className="responses-list">
                                      {Object.entries(checkData.responses).map(([question, answer], idx) => (
                                         <div key={idx} className="mb-3 p-3 bg-light rounded-2">
                                            <small className="text-muted d-block mb-1 text-uppercase fw-bold" style={{fontSize: '0.7rem'}}>Domanda {idx + 1}</small>
                                            <div className="fw-semibold text-dark mb-1">{question}</div>
                                            <div className="text-secondary" style={{whiteSpace: 'pre-wrap'}}>{Array.isArray(answer) ? answer.join(', ') : String(answer)}</div>
                                         </div>
                                      ))}
                                   </div>
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
                    <div className="text-center py-5">
                      <div className="spinner-border text-primary" role="status"></div>
                      <p className="mt-2 text-muted">Caricamento ticket...</p>
                    </div>
                  ) : patientTickets.length === 0 ? (
                    <div className="text-center py-5">
                      <i className="ri-ticket-2-line" style={{ fontSize: '3rem', color: '#d1d5db' }}></i>
                      <p className="mt-3 text-muted">Nessun ticket associato a questo paziente</p>
                    </div>
                  ) : (
                    <div className="table-responsive">
                      <table className="table table-hover align-middle mb-0">
                        <thead className="bg-light">
                          <tr>
                            <th className="small text-uppercase text-muted fw-semibold">Numero</th>
                            <th className="small text-uppercase text-muted fw-semibold">Titolo</th>
                            <th className="small text-uppercase text-muted fw-semibold">Stato</th>
                            <th className="small text-uppercase text-muted fw-semibold">Priorita'</th>
                            <th className="small text-uppercase text-muted fw-semibold">Assegnatari</th>
                            <th className="small text-uppercase text-muted fw-semibold">Fonte</th>
                            <th className="small text-uppercase text-muted fw-semibold">Data</th>
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
                              <tr key={t.id} style={{ cursor: 'pointer' }} onClick={() => openTicketDetail(t.id)}>
                                <td><span className="fw-semibold text-primary">{t.ticket_number}</span></td>
                                <td>{t.title || <span className="text-muted fst-italic">{(t.description || '').slice(0, 50)}</span>}</td>
                                <td>
                                  <span className="badge rounded-pill px-2 py-1" style={{ background: statusCfg.bg, color: statusCfg.color, fontSize: '0.75rem' }}>
                                    {statusCfg.label}
                                  </span>
                                </td>
                                <td>
                                  <span className="badge rounded-pill px-2 py-1" style={{ background: prioCfg.bg, color: prioCfg.color, fontSize: '0.75rem' }}>
                                    {prioCfg.label}
                                  </span>
                                </td>
                                <td>
                                  <span className="small text-muted">
                                    {(t.assigned_users || []).map(u => u.name).join(', ') || '—'}
                                  </span>
                                </td>
                                <td>
                                  <i className={`ri-${t.source === 'teams' ? 'microsoft-line text-primary' : 'computer-line text-secondary'}`}></i>
                                </td>
                                <td><small className="text-muted">{t.created_at ? new Date(t.created_at).toLocaleDateString('it-IT') : '—'}</small></td>
                                <td>
                                  <span className="text-muted small">
                                    {t.messages_count > 0 && <span className="me-2"><i className="ri-chat-3-line"></i> {t.messages_count}</span>}
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
                <div>
                  <div className="d-flex justify-content-between align-items-center mb-4">
                    <h5 className="mb-0">
                      <i className="ri-phone-line me-2 text-primary"></i>
                      Storico Call Bonus
                    </h5>
                    {(user?.is_admin || user?.role === 'admin' ||
                      (c.nutrizionistiMultipli || []).some(n => n.id === user?.id) ||
                      (c.coachesMultipli || []).some(n => n.id === user?.id) ||
                      (c.psicologiMultipli || []).some(n => n.id === user?.id)
                    ) && (
                      <button className="btn btn-primary" onClick={handleOpenCallBonusModal}>
                        <i className="ri-add-line me-1"></i>Richiedi Call Bonus
                      </button>
                    )}
                  </div>

                  {loadingCallBonus ? (
                    <div className="text-center py-5">
                      <div className="spinner-border text-primary" role="status"></div>
                      <p className="mt-2 text-muted">Caricamento storico...</p>
                    </div>
                  ) : callBonusHistory.length === 0 ? (
                    <div className="text-center py-5">
                      <i className="ri-phone-line" style={{ fontSize: '3rem', color: '#d1d5db' }}></i>
                      <p className="mt-3 text-muted">Nessuna call bonus registrata per questo paziente</p>
                    </div>
                  ) : (
                    <div className="table-responsive">
                      <table className="table table-hover align-middle mb-0">
                        <thead className="bg-light">
                          <tr>
                            <th className="small text-uppercase text-muted fw-semibold">Data</th>
                            <th className="small text-uppercase text-muted fw-semibold">Tipo</th>
                            <th className="small text-uppercase text-muted fw-semibold">Professionista</th>
                            <th className="small text-uppercase text-muted fw-semibold">Stato</th>
                            <th className="small text-uppercase text-muted fw-semibold">Richiesta da</th>
                            <th className="small text-uppercase text-muted fw-semibold">Note</th>
                            <th className="small text-uppercase text-muted fw-semibold">Azioni</th>
                          </tr>
                        </thead>
                        <tbody>
                          {callBonusHistory.map((cb) => {
                            const statusCfg = {
                              proposta: { label: 'Proposta', bg: '#fef3c7', color: '#92400e' },
                              accettata: { label: 'Accettata', bg: '#dbeafe', color: '#1e40af' },
                              rifiutata: { label: 'Rifiutata', bg: '#fee2e2', color: '#991b1b' },
                              confermata: { label: 'Confermata', bg: '#d1fae5', color: '#065f46' },
                              non_andata_buon_fine: { label: 'Non andata a buon fine', bg: '#f3f4f6', color: '#374151' },
                            }[cb.status] || { label: cb.status, bg: '#f3f4f6', color: '#374151' };
                            const tipoCfg = {
                              nutrizionista: { label: 'Nutrizione', icon: 'ri-heart-pulse-line', color: '#10b981' },
                              coach: { label: 'Coaching', icon: 'ri-run-line', color: '#6366f1' },
                              psicologa: { label: 'Psicologia', icon: 'ri-mental-health-line', color: '#ec4899' },
                            }[cb.tipo_professionista] || { label: cb.tipo_professionista, icon: 'ri-user-line', color: '#6b7280' };
                            const showActions = cb.is_assigned_professional && cb.status === 'accettata' && !cb.booking_confirmed;
                            return (
                              <tr key={cb.id}>
                                <td><small className="text-muted">{cb.data_richiesta ? new Date(cb.data_richiesta).toLocaleDateString('it-IT') : '—'}</small></td>
                                <td>
                                  <span className="d-flex align-items-center gap-1">
                                    <i className={tipoCfg.icon} style={{ color: tipoCfg.color }}></i>
                                    <span className="small">{tipoCfg.label}</span>
                                  </span>
                                </td>
                                <td><span className="small">{cb.professionista_nome || '—'}</span></td>
                                <td>
                                  <span className="badge rounded-pill px-2 py-1" style={{ background: statusCfg.bg, color: statusCfg.color, fontSize: '0.75rem' }}>
                                    {statusCfg.label}
                                  </span>
                                  {cb.booking_confirmed && (
                                    <i className="ri-calendar-check-line text-success ms-1" title="Prenotazione confermata"></i>
                                  )}
                                </td>
                                <td><span className="small text-muted">{cb.created_by_nome || '—'}</span></td>
                                <td><span className="small text-muted">{cb.note_richiesta ? (cb.note_richiesta.length > 50 ? cb.note_richiesta.slice(0, 50) + '...' : cb.note_richiesta) : '—'}</span></td>
                                <td>
                                  {showActions && (
                                    <button
                                      className="btn btn-sm btn-primary"
                                      onClick={() => setCallBonusResponseModal(cb)}
                                    >
                                      <i className="ri-reply-line me-1"></i>Rispondi
                                    </button>
                                  )}
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
            </div>
          </div>
        </div>
      </div>

      {/* ========== TICKET DETAIL MODAL ========== */}
      {(ticketDetailModal || loadingTicketDetail) && (
        <div className="modal show d-block" style={{ background: 'rgba(0,0,0,0.5)' }} onClick={() => { setTicketDetailModal(null); setTicketMessages([]); }}>
          <div className="modal-dialog modal-dialog-centered modal-lg" onClick={(e) => e.stopPropagation()}>
            <div className="modal-content" style={{ maxHeight: '85vh', overflow: 'hidden' }}>
              {loadingTicketDetail && !ticketDetailModal ? (
                <div className="modal-body text-center py-5">
                  <div className="spinner-border text-primary" role="status"></div>
                  <p className="mt-2 text-muted">Caricamento...</p>
                </div>
              ) : ticketDetailModal && (
                <>
                  <div className="modal-header border-0" style={{ background: 'linear-gradient(135deg, rgba(99, 102, 241, 0.08) 0%, rgba(139, 92, 246, 0.08) 100%)' }}>
                    <div>
                      <div className="d-flex align-items-center gap-2 mb-1">
                        <h5 className="modal-title mb-0">
                          <i className="ri-ticket-2-line me-2 text-primary"></i>
                          {ticketDetailModal.ticket_number}
                        </h5>
                        <span className="badge rounded-pill px-2 py-1" style={{
                          background: ({ aperto: '#fef3c7', in_lavorazione: '#dbeafe', risolto: '#d1fae5', chiuso: '#f3f4f6' })[ticketDetailModal.status] || '#f3f4f6',
                          color: ({ aperto: '#92400e', in_lavorazione: '#1e40af', risolto: '#065f46', chiuso: '#374151' })[ticketDetailModal.status] || '#374151',
                          fontSize: '0.7rem',
                        }}>
                          {({ aperto: 'Aperto', in_lavorazione: 'In Lavorazione', risolto: 'Risolto', chiuso: 'Chiuso' })[ticketDetailModal.status] || ticketDetailModal.status}
                        </span>
                        <span className="badge rounded-pill px-2 py-1" style={{
                          background: ({ alta: '#fee2e2', media: '#fef9c3', bassa: '#dcfce7' })[ticketDetailModal.priority] || '#f3f4f6',
                          color: ({ alta: '#991b1b', media: '#854d0e', bassa: '#166534' })[ticketDetailModal.priority] || '#374151',
                          fontSize: '0.7rem',
                        }}>
                          {({ alta: 'Alta', media: 'Media', bassa: 'Bassa' })[ticketDetailModal.priority] || ticketDetailModal.priority}
                        </span>
                        <i className={`ri-${ticketDetailModal.source === 'teams' ? 'microsoft-line text-primary' : 'computer-line text-secondary'}`}></i>
                      </div>
                      <span className="text-muted small">{ticketDetailModal.title || '(Senza titolo)'}</span>
                    </div>
                    <button className="btn-close" onClick={() => { setTicketDetailModal(null); setTicketMessages([]); }}></button>
                  </div>
                  <div className="modal-body" style={{ overflowY: 'auto', maxHeight: 'calc(85vh - 140px)' }}>
                    {/* Info */}
                    <div className="row g-3 mb-4">
                      <div className="col-sm-6">
                        <div className="small text-muted text-uppercase fw-semibold mb-1">Assegnatari</div>
                        <div>{(ticketDetailModal.assigned_users || []).map(u => u.name).join(', ') || 'Nessuno'}</div>
                      </div>
                      <div className="col-sm-6">
                        <div className="small text-muted text-uppercase fw-semibold mb-1">Creato da</div>
                        <div>{ticketDetailModal.created_by_name || 'Teams'} — {ticketDetailModal.created_at ? new Date(ticketDetailModal.created_at).toLocaleString('it-IT') : '—'}</div>
                      </div>
                      {ticketDetailModal.resolved_at && (
                        <div className="col-sm-6">
                          <div className="small text-muted text-uppercase fw-semibold mb-1">Risolto il</div>
                          <div>{new Date(ticketDetailModal.resolved_at).toLocaleString('it-IT')}</div>
                        </div>
                      )}
                      {ticketDetailModal.closed_at && (
                        <div className="col-sm-6">
                          <div className="small text-muted text-uppercase fw-semibold mb-1">Chiuso il</div>
                          <div>{new Date(ticketDetailModal.closed_at).toLocaleString('it-IT')}</div>
                        </div>
                      )}
                    </div>

                    {/* Descrizione */}
                    {ticketDetailModal.description && (
                      <div className="mb-4">
                        <div className="small text-muted text-uppercase fw-semibold mb-2">Descrizione</div>
                        <div className="p-3 bg-light rounded" style={{ whiteSpace: 'pre-wrap' }}>{ticketDetailModal.description}</div>
                      </div>
                    )}

                    {/* Allegati */}
                    {ticketDetailModal.attachments && ticketDetailModal.attachments.length > 0 && (
                      <div className="mb-4">
                        <div className="small text-muted text-uppercase fw-semibold mb-2">
                          <i className="ri-attachment-2 me-1"></i>Allegati ({ticketDetailModal.attachments.length})
                        </div>
                        <div className="d-flex flex-wrap gap-2">
                          {ticketDetailModal.attachments.map((att) => {
                            const sizeKb = att.file_size ? (att.file_size / 1024).toFixed(0) : '?';
                            return (
                              <a
                                key={att.id}
                                href={teamTicketsService.getAttachmentUrl(att.id)}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="btn btn-sm btn-outline-secondary d-inline-flex align-items-center gap-1"
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
                        <div className="small text-muted text-uppercase fw-semibold mb-2">
                          <i className="ri-chat-3-line me-1"></i>Messaggi ({ticketMessages.length})
                        </div>
                        <div className="d-flex flex-column gap-2">
                          {ticketMessages.map((msg) => (
                            <div
                              key={msg.id}
                              className="p-2 rounded"
                              style={{
                                background: msg.source === 'teams' ? 'rgba(99, 102, 241, 0.06)' : 'rgba(16, 185, 129, 0.06)',
                                borderLeft: `3px solid ${msg.source === 'teams' ? '#6366f1' : '#10b981'}`,
                              }}
                            >
                              <div className="d-flex justify-content-between align-items-center mb-1">
                                <span className="fw-semibold small">
                                  <i className={`ri-${msg.source === 'teams' ? 'microsoft-line text-primary' : 'computer-line text-success'} me-1`}></i>
                                  {msg.sender_name || 'Anonimo'}
                                </span>
                                <small className="text-muted">{msg.created_at ? new Date(msg.created_at).toLocaleString('it-IT') : ''}</small>
                              </div>
                              <div className="small" style={{ whiteSpace: 'pre-wrap' }}>{msg.content}</div>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                  <div className="modal-footer border-0">
                    <button className="btn btn-secondary" onClick={() => { setTicketDetailModal(null); setTicketMessages([]); }}>Chiudi</button>
                  </div>
                </>
              )}
            </div>
          </div>
        </div>
      )}

      {/* ========== CALL BONUS MODAL (3 steps) ========== */}
      {showCallBonusModal && (
        <div className="modal show d-block" style={{ background: 'rgba(0,0,0,0.5)' }}>
          <div className="modal-dialog modal-dialog-centered modal-lg">
            <div className="modal-content">
              <div className="modal-header border-0" style={{ background: 'linear-gradient(135deg, rgba(99, 102, 241, 0.1) 0%, rgba(139, 92, 246, 0.1) 100%)' }}>
                <h5 className="modal-title">
                  <i className="ri-phone-line me-2 text-primary"></i>
                  Richiedi Call Bonus
                  <span className="badge bg-primary ms-2" style={{ fontSize: '0.65rem' }}>Step {callBonusStep}/3</span>
                </h5>
                <button className="btn-close" onClick={() => setShowCallBonusModal(false)}></button>
              </div>
              <div className="modal-body">

                {/* ── STEP 1: Tipo + Note ── */}
                {callBonusStep === 1 && (
                  <div>
                    <p className="text-muted small mb-3">Seleziona il tipo di professionista e descrivi l'obiettivo della call bonus.</p>

                    <div className="mb-4">
                      <label className="form-label small text-muted fw-semibold">Tipo Professionista *</label>
                      <div className="d-flex gap-2">
                        {[
                          { value: 'coach', label: 'Coaching', icon: 'ri-run-line', color: '#6366f1', bg: 'rgba(99,102,241,0.1)' },
                          { value: 'nutrizionista', label: 'Nutrizione', icon: 'ri-heart-pulse-line', color: '#10b981', bg: 'rgba(16,185,129,0.1)' },
                          { value: 'psicologa', label: 'Psicologia', icon: 'ri-mental-health-line', color: '#ec4899', bg: 'rgba(236,72,153,0.1)' },
                        ].map((t) => (
                          <button
                            key={t.value}
                            className={`btn flex-fill d-flex flex-column align-items-center gap-1 py-3 ${callBonusForm.tipo_professionista === t.value ? 'border-2' : ''}`}
                            style={{
                              background: callBonusForm.tipo_professionista === t.value ? t.bg : '#f9fafb',
                              borderColor: callBonusForm.tipo_professionista === t.value ? t.color : '#e5e7eb',
                              color: t.color,
                              borderRadius: '12px',
                            }}
                            onClick={() => setCallBonusForm({ ...callBonusForm, tipo_professionista: t.value })}
                          >
                            <i className={t.icon} style={{ fontSize: '1.5rem' }}></i>
                            <span className="small fw-semibold">{t.label}</span>
                          </button>
                        ))}
                      </div>
                    </div>

                    <div className="mb-3">
                      <label className="form-label small text-muted fw-semibold">Motivazione / Obiettivo</label>
                      <textarea
                        className="form-control"
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
                      <div className="mb-4 p-3 rounded-3" style={{ background: 'linear-gradient(135deg, rgba(99, 102, 241, 0.05) 0%, rgba(139, 92, 246, 0.05) 100%)', border: '1px solid rgba(99, 102, 241, 0.15)' }}>
                        <div className="d-flex align-items-center gap-2 mb-2">
                          <i className="ri-robot-2-line text-primary"></i>
                          <span className="fw-semibold small">Analisi SuiteMind AI</span>
                        </div>
                        {callBonusAnalysis.summary && (
                          <p className="small text-muted mb-2">{callBonusAnalysis.summary}</p>
                        )}
                        {callBonusAnalysis.suggested_focus && callBonusAnalysis.suggested_focus.length > 0 && (
                          <div className="d-flex flex-wrap gap-1">
                            {callBonusAnalysis.suggested_focus.map((f, i) => (
                              <span key={i} className="badge rounded-pill" style={{ background: 'rgba(99,102,241,0.1)', color: '#6366f1', fontSize: '0.7rem' }}>
                                {f}
                              </span>
                            ))}
                          </div>
                        )}
                      </div>
                    )}

                    {/* Professional matches */}
                    <p className="text-muted small mb-3">Seleziona il professionista per la call bonus:</p>
                    {callBonusMatches.length === 0 ? (
                      <div className="text-center py-4">
                        <i className="ri-user-search-line" style={{ fontSize: '2rem', color: '#d1d5db' }}></i>
                        <p className="mt-2 text-muted small">Nessun professionista trovato per i criteri selezionati.</p>
                      </div>
                    ) : (
                      <div className="d-flex flex-column gap-2">
                        {callBonusMatches.map((prof) => (
                          <div
                            key={prof.id}
                            className="p-3 rounded-3 d-flex align-items-center gap-3"
                            style={{
                              background: '#f9fafb',
                              border: '1px solid #e5e7eb',
                              cursor: 'pointer',
                              transition: 'all 0.2s',
                            }}
                            onClick={() => handleSelectCallBonusProfessional(prof)}
                            onMouseOver={(e) => { e.currentTarget.style.borderColor = '#6366f1'; e.currentTarget.style.background = 'rgba(99,102,241,0.03)'; }}
                            onMouseOut={(e) => { e.currentTarget.style.borderColor = '#e5e7eb'; e.currentTarget.style.background = '#f9fafb'; }}
                          >
                            {/* Avatar */}
                            <div className="rounded-circle d-flex align-items-center justify-content-center" style={{ width: 44, height: 44, background: 'linear-gradient(135deg, #6366f1, #8b5cf6)', color: '#fff', fontWeight: 600, fontSize: '0.9rem', flexShrink: 0 }}>
                              {prof.name ? prof.name.split(' ').map(n => n[0]).join('').slice(0, 2).toUpperCase() : '??'}
                            </div>
                            {/* Info */}
                            <div className="flex-grow-1">
                              <div className="fw-semibold small">{prof.name}</div>
                              {prof.match_reasons && prof.match_reasons.length > 0 && (
                                <div className="d-flex flex-wrap gap-1 mt-1">
                                  {prof.match_reasons.slice(0, 4).map((r, i) => (
                                    <span key={i} className="badge rounded-pill" style={{ background: 'rgba(16,185,129,0.1)', color: '#10b981', fontSize: '0.65rem' }}>
                                      {r}
                                    </span>
                                  ))}
                                  {prof.match_reasons.length > 4 && (
                                    <span className="badge rounded-pill" style={{ background: '#f3f4f6', color: '#6b7280', fontSize: '0.65rem' }}>
                                      +{prof.match_reasons.length - 4}
                                    </span>
                                  )}
                                </div>
                              )}
                            </div>
                            {/* Score */}
                            <div className="text-end" style={{ minWidth: 70 }}>
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
                  <div className="text-center">
                    <div className="mb-4">
                      <div className="rounded-circle d-inline-flex align-items-center justify-content-center mb-3" style={{ width: 64, height: 64, background: 'linear-gradient(135deg, #6366f1, #8b5cf6)', color: '#fff', fontWeight: 600, fontSize: '1.3rem' }}>
                        {selectedCallBonusProfessional.name ? selectedCallBonusProfessional.name.split(' ').map(n => n[0]).join('').slice(0, 2).toUpperCase() : '??'}
                      </div>
                      <h6 className="mb-1">{selectedCallBonusProfessional.name}</h6>
                      <span className="badge rounded-pill" style={{ background: 'rgba(99,102,241,0.1)', color: '#6366f1' }}>
                        Selezionato
                      </span>
                    </div>

                    {callBonusCalendarLink ? (
                      <div className="mb-4">
                        <a
                          href={callBonusCalendarLink}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="btn btn-outline-primary btn-lg d-inline-flex align-items-center gap-2"
                        >
                          <i className="ri-calendar-line"></i>
                          Apri Calendario Call Bonus
                          <i className="ri-external-link-line"></i>
                        </a>
                        <p className="text-muted small mt-2">Clicca per prenotare la call bonus nel calendario del professionista.</p>
                      </div>
                    ) : (
                      <div className="alert alert-warning d-inline-flex align-items-center gap-2 mb-4" role="alert">
                        <i className="ri-error-warning-line"></i>
                        <span className="small">Il professionista non ha configurato un link calendario per le call bonus.</span>
                      </div>
                    )}
                  </div>
                )}

              </div>
              <div className="modal-footer border-0">
                {callBonusStep === 1 && (
                  <>
                    <button className="btn btn-secondary" onClick={() => setShowCallBonusModal(false)}>Annulla</button>
                    <button
                      className="btn btn-primary"
                      onClick={handleCallBonusAnalyze}
                      disabled={!callBonusForm.tipo_professionista || callBonusAiLoading}
                    >
                      {callBonusAiLoading ? (
                        <><span className="spinner-border spinner-border-sm me-2"></span>Analisi in corso...</>
                      ) : (
                        <><i className="ri-robot-2-line me-1"></i>Analizza con SuiteMind AI</>
                      )}
                    </button>
                  </>
                )}
                {callBonusStep === 2 && (
                  <button className="btn btn-secondary" onClick={() => setCallBonusStep(1)}>
                    <i className="ri-arrow-left-line me-1"></i>Indietro
                  </button>
                )}
                {callBonusStep === 3 && (
                  <>
                    <button className="btn btn-secondary" onClick={() => setCallBonusStep(2)}>
                      <i className="ri-arrow-left-line me-1"></i>Indietro
                    </button>
                    <button
                      className="btn btn-success"
                      onClick={handleConfirmCallBonusBooking}
                      disabled={confirmingBooking}
                    >
                      {confirmingBooking ? (
                        <><span className="spinner-border spinner-border-sm me-2"></span>Conferma...</>
                      ) : (
                        <><i className="ri-check-line me-1"></i>Ho prenotato la call</>
                      )}
                    </button>
                  </>
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Call Bonus Response Modal (professionista) */}
      {callBonusResponseModal && (
        <div className="modal show d-block" style={{ background: 'rgba(0,0,0,0.5)' }} onClick={() => setCallBonusResponseModal(null)}>
          <div className="modal-dialog modal-dialog-centered" onClick={(e) => e.stopPropagation()}>
            <div className="modal-content">
              <div className="modal-header border-0" style={{ background: 'linear-gradient(135deg, rgba(99, 102, 241, 0.1) 0%, rgba(139, 92, 246, 0.1) 100%)' }}>
                <h5 className="modal-title">
                  <i className="ri-phone-line me-2 text-primary"></i>
                  Risposta Call Bonus
                </h5>
                <button className="btn-close" onClick={() => setCallBonusResponseModal(null)}></button>
              </div>
              <div className="modal-body text-center">
                {/* Info richiesta */}
                <div className="mb-4 p-3 rounded-3" style={{ background: '#f9fafb', border: '1px solid #e5e7eb' }}>
                  <p className="small text-muted mb-1">Richiesta da <strong>{callBonusResponseModal.created_by_nome}</strong></p>
                  {callBonusResponseModal.note_richiesta && (
                    <p className="small mb-0 fst-italic">"{callBonusResponseModal.note_richiesta}"</p>
                  )}
                </div>

                {/* Calendario HM */}
                <div className="mb-4">
                  <p className="small fw-semibold mb-2">
                    <i className="ri-calendar-line me-1 text-primary"></i>
                    Calendario Health Manager{callBonusResponseModal.hm_name ? ` — ${callBonusResponseModal.hm_name}` : ''}
                  </p>
                  {callBonusResponseModal.hm_calendar_link ? (
                    <a
                      href={callBonusResponseModal.hm_calendar_link}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="btn btn-outline-primary d-inline-flex align-items-center gap-2"
                    >
                      <i className="ri-calendar-line"></i>
                      Apri Calendario
                      <i className="ri-external-link-line"></i>
                    </a>
                  ) : (
                    <div className="alert alert-warning d-inline-flex align-items-center gap-2 mb-0" role="alert">
                      <i className="ri-error-warning-line"></i>
                      <span className="small">Link calendario HM non disponibile.</span>
                    </div>
                  )}
                  <p className="text-muted small mt-2">Prenota la call bonus nel calendario dell'Health Manager, poi conferma.</p>
                </div>
              </div>
              <div className="modal-footer border-0 d-flex justify-content-between">
                <button
                  className="btn btn-danger"
                  onClick={handleDeclineCallBonus}
                  disabled={decliningCallBonus}
                >
                  {decliningCallBonus ? (
                    <><span className="spinner-border spinner-border-sm me-2"></span>Rifiuto...</>
                  ) : (
                    <><i className="ri-thumb-down-line me-1"></i>Non interessato</>
                  )}
                </button>
                <button
                  className="btn btn-success"
                  onClick={handleConfirmCallBonusBooking}
                  disabled={confirmingBooking}
                >
                  {confirmingBooking ? (
                    <><span className="spinner-border spinner-border-sm me-2"></span>Conferma...</>
                  ) : (
                    <><i className="ri-check-line me-1"></i>Ho prenotato la call</>
                  )}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Delete Modal */}
      {showDeleteModal && (
        <div className="modal show d-block" style={{ background: 'rgba(0,0,0,0.5)' }}>
          <div className="modal-dialog modal-dialog-centered">
            <div className="modal-content">
              <div className="modal-header border-0">
                <h5 className="modal-title">Conferma Eliminazione</h5>
                <button className="btn-close" onClick={() => setShowDeleteModal(false)}></button>
              </div>
              <div className="modal-body">
                <p>Sei sicuro di voler eliminare <strong>{c.nome}</strong>?</p>
                <p className="text-danger small">Questa azione non può essere annullata.</p>
              </div>
              <div className="modal-footer border-0">
                <button className="btn btn-secondary" onClick={() => setShowDeleteModal(false)}>Annulla</button>
                <button className="btn btn-danger" onClick={handleDelete} disabled={deleting}>
                  {deleting ? <><span className="spinner-border spinner-border-sm me-2"></span>Eliminazione...</> : <><i className="ri-delete-bin-line me-2"></i>Elimina</>}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Assign Professional Modal */}
      {showAssignModal && (
        <div className="modal show d-block" style={{ background: 'rgba(0,0,0,0.5)' }}>
          <div className="modal-dialog modal-dialog-centered">
            <div className="modal-content">
              <div className="modal-header border-0">
                <h5 className="modal-title">
                  <i className={`${TIPO_PROFESSIONISTA_ICONS[assigningType]} me-2`}></i>
                  Assegna {TIPO_PROFESSIONISTA_LABELS[assigningType]}
                </h5>
                <button className="btn-close" onClick={() => setShowAssignModal(false)}></button>
              </div>
              <div className="modal-body">
                <div className="mb-3">
                  <label className="form-label small text-muted">Professionista *</label>
                  <select
                    className="form-select"
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
                <div className="mb-3">
                  <label className="form-label small text-muted">Data Inizio Assegnazione *</label>
                  <input
                    type="date"
                    className="form-control"
                    value={assignForm.data_dal}
                    onChange={(e) => setAssignForm({ ...assignForm, data_dal: e.target.value })}
                  />
                </div>
                <div className="mb-3">
                  <label className="form-label small text-muted">Motivazione Assegnazione *</label>
                  <textarea
                    className="form-control"
                    rows="3"
                    placeholder="Es: Inizio percorso, Cambio professionista per compatibilità, Nuova fase del programma..."
                    value={assignForm.motivazione_aggiunta}
                    onChange={(e) => setAssignForm({ ...assignForm, motivazione_aggiunta: e.target.value })}
                  ></textarea>
                </div>
              </div>
              <div className="modal-footer border-0">
                <button className="btn btn-secondary" onClick={() => setShowAssignModal(false)} disabled={assignLoading}>
                  Annulla
                </button>
                <button className="btn btn-primary" onClick={handleAssignProfessional} disabled={assignLoading}>
                  {assignLoading ? (
                    <><span className="spinner-border spinner-border-sm me-2"></span>Assegnazione...</>
                  ) : (
                    <><i className="ri-check-line me-2"></i>Assegna</>
                  )}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Interrupt Assignment Modal */}
      {showInterruptModal && interruptingAssignment && (
        <div className="modal show d-block" style={{ background: 'rgba(0,0,0,0.5)' }}>
          <div className="modal-dialog modal-dialog-centered">
            <div className="modal-content">
              <div className="modal-header border-0">
                <h5 className="modal-title">
                  <i className="ri-user-unfollow-line me-2 text-danger"></i>
                  Rimuovi Assegnazione
                </h5>
                <button className="btn-close" onClick={() => setShowInterruptModal(false)}></button>
              </div>
              <div className="modal-body">
                <div className="alert alert-warning mb-3">
                  <div className="d-flex align-items-center">
                    <i className={`${TIPO_PROFESSIONISTA_ICONS[interruptingAssignment.tipo_professionista]} me-2 fs-4`}></i>
                    <div>
                      <strong>{interruptingAssignment.professionista_nome}</strong>
                      <div className="small text-muted">
                        {TIPO_PROFESSIONISTA_LABELS[interruptingAssignment.tipo_professionista]} • dal {interruptingAssignment.data_dal}
                      </div>
                    </div>
                  </div>
                </div>
                <div className="mb-3">
                  <label className="form-label small text-muted">Motivazione Interruzione *</label>
                  <textarea
                    className="form-control"
                    rows="3"
                    placeholder="Es: Fine percorso, Cambio professionista, Incompatibilità, Richiesta cliente..."
                    value={interruptForm.motivazione_interruzione}
                    onChange={(e) => setInterruptForm({ ...interruptForm, motivazione_interruzione: e.target.value })}
                  ></textarea>
                </div>
              </div>
              <div className="modal-footer border-0">
                <button className="btn btn-secondary" onClick={() => setShowInterruptModal(false)} disabled={assignLoading}>
                  Annulla
                </button>
                <button className="btn btn-danger" onClick={handleInterruptAssignment} disabled={assignLoading}>
                  {assignLoading ? (
                    <><span className="spinner-border spinner-border-sm me-2"></span>Rimozione...</>
                  ) : (
                    <><i className="ri-close-line me-2"></i>Rimuovi Assegnazione</>
                  )}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Add Meal Plan Modal */}
      {showAddMealPlanModal && (
        <div className="modal show d-block" style={{ background: 'rgba(0,0,0,0.5)' }}>
          <div className="modal-dialog modal-dialog-centered">
            <div className="modal-content">
              <div className="modal-header border-0" style={{ background: 'linear-gradient(135deg, rgba(34, 197, 94, 0.1) 0%, rgba(16, 185, 129, 0.1) 100%)' }}>
                <h5 className="modal-title">
                  <i className="ri-restaurant-line me-2 text-success"></i>
                  Nuovo Piano Alimentare
                </h5>
                <button className="btn-close" onClick={() => setShowAddMealPlanModal(false)}></button>
              </div>
              <div className="modal-body">
                <div className="mb-3">
                  <label className="form-label small text-muted">Nome Piano (opzionale)</label>
                  <input
                    type="text"
                    className="form-control"
                    placeholder="Es: Piano Alimentare Gennaio 2026"
                    value={mealPlanForm.name}
                    onChange={(e) => setMealPlanForm({ ...mealPlanForm, name: e.target.value })}
                  />
                  <small className="text-muted">Se vuoto, verrà generato automaticamente</small>
                </div>
                <div className="row mb-3">
                  <div className="col-6">
                    <label className="form-label small text-muted">Data Inizio *</label>
                    <input
                      type="date"
                      className="form-control"
                      value={mealPlanForm.start_date}
                      onChange={(e) => setMealPlanForm({ ...mealPlanForm, start_date: e.target.value })}
                    />
                  </div>
                  <div className="col-6">
                    <label className="form-label small text-muted">Data Fine *</label>
                    <input
                      type="date"
                      className="form-control"
                      value={mealPlanForm.end_date}
                      onChange={(e) => setMealPlanForm({ ...mealPlanForm, end_date: e.target.value })}
                    />
                  </div>
                </div>
                <div className="mb-3">
                  <label className="form-label small text-muted">Piano Alimentare (PDF) *</label>
                  <input
                    type="file"
                    className="form-control"
                    accept=".pdf"
                    onChange={(e) => setMealPlanFile(e.target.files[0])}
                  />
                  <small className="text-muted">Carica il piano alimentare in formato PDF (max 50MB)</small>
                </div>
                <div className="mb-3">
                  <label className="form-label small text-muted">Note (opzionale)</label>
                  <textarea
                    className="form-control"
                    rows="2"
                    placeholder="Note aggiuntive..."
                    value={mealPlanForm.notes}
                    onChange={(e) => setMealPlanForm({ ...mealPlanForm, notes: e.target.value })}
                  ></textarea>
                </div>
              </div>
              <div className="modal-footer border-0">
                <button
                  className="btn btn-secondary"
                  onClick={() => {
                    setShowAddMealPlanModal(false);
                    setMealPlanForm({ name: '', start_date: '', end_date: '', notes: '' });
                    setMealPlanFile(null);
                  }}
                  disabled={savingMealPlan}
                >
                  Annulla
                </button>
                <button className="btn btn-success" onClick={handleAddMealPlan} disabled={savingMealPlan}>
                  {savingMealPlan ? (
                    <><span className="spinner-border spinner-border-sm me-2"></span>Salvataggio...</>
                  ) : (
                    <><i className="ri-save-line me-2"></i>Salva Piano</>
                  )}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Preview Meal Plan PDF Modal */}
      {showPreviewPlanModal && selectedPlan && (
        <div className="modal show d-block" style={{ background: 'rgba(0,0,0,0.5)' }} onClick={() => setShowPreviewPlanModal(false)}>
          <div className="modal-dialog modal-dialog-centered modal-xl" onClick={(e) => e.stopPropagation()}>
            <div className="modal-content" style={{ height: '90vh' }}>
              <div className="modal-header border-0" style={{ background: 'linear-gradient(135deg, rgba(34, 197, 94, 0.1) 0%, rgba(16, 185, 129, 0.1) 100%)' }}>
                <h5 className="modal-title">
                  <i className="ri-file-pdf-line me-2 text-success"></i>
                  {selectedPlan.name || 'Piano Alimentare'}
                </h5>
                <div className="d-flex gap-2 align-items-center">
                  <a
                    href={`/uploads/${selectedPlan.piano_alimentare_file_path}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="btn btn-sm btn-outline-success"
                  >
                    <i className="ri-download-line me-1"></i>
                    Scarica
                  </a>
                  <button className="btn-close" onClick={() => setShowPreviewPlanModal(false)}></button>
                </div>
              </div>
              <div className="modal-body p-0" style={{ height: 'calc(100% - 60px)' }}>
                <iframe
                  src={`/uploads/${selectedPlan.piano_alimentare_file_path}`}
                  style={{ width: '100%', height: '100%', border: 'none' }}
                  title="Piano Alimentare PDF"
                />
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Edit Meal Plan Modal */}
      {showEditPlanModal && selectedPlan && (
        <div className="modal show d-block" style={{ background: 'rgba(0,0,0,0.5)' }}>
          <div className="modal-dialog modal-dialog-centered">
            <div className="modal-content">
              <div className="modal-header border-0" style={{ background: 'linear-gradient(135deg, rgba(59, 130, 246, 0.1) 0%, rgba(37, 99, 235, 0.1) 100%)' }}>
                <h5 className="modal-title">
                  <i className="ri-edit-line me-2 text-primary"></i>
                  Modifica Piano Alimentare
                </h5>
                <button className="btn-close" onClick={() => setShowEditPlanModal(false)}></button>
              </div>
              <div className="modal-body">
                <div className="alert alert-info small mb-3">
                  <i className="ri-information-line me-1"></i>
                  Stai modificando: <strong>{selectedPlan.name || 'Piano Alimentare'}</strong>
                </div>
                <div className="row mb-3">
                  <div className="col-6">
                    <label className="form-label small text-muted">Data Inizio *</label>
                    <input
                      type="date"
                      className="form-control"
                      value={editPlanForm.start_date}
                      onChange={(e) => setEditPlanForm({ ...editPlanForm, start_date: e.target.value })}
                    />
                  </div>
                  <div className="col-6">
                    <label className="form-label small text-muted">Data Fine *</label>
                    <input
                      type="date"
                      className="form-control"
                      value={editPlanForm.end_date}
                      onChange={(e) => setEditPlanForm({ ...editPlanForm, end_date: e.target.value })}
                    />
                  </div>
                </div>
                <div className="mb-3">
                  <label className="form-label small text-muted">Nuovo PDF (opzionale)</label>
                  <input
                    type="file"
                    className="form-control"
                    accept=".pdf"
                    onChange={(e) => setEditPlanFile(e.target.files[0])}
                  />
                  <small className="text-muted">Lascia vuoto per mantenere il PDF esistente</small>
                </div>
                <div className="mb-3">
                  <label className="form-label small text-muted">Note (opzionale)</label>
                  <textarea
                    className="form-control"
                    rows="2"
                    placeholder="Note aggiuntive..."
                    value={editPlanForm.notes}
                    onChange={(e) => setEditPlanForm({ ...editPlanForm, notes: e.target.value })}
                  ></textarea>
                </div>
                <div className="mb-3">
                  <label className="form-label small text-muted">Motivo della modifica</label>
                  <input
                    type="text"
                    className="form-control"
                    placeholder="Es: Aggiornamento calorie settimanali"
                    value={editPlanForm.change_reason}
                    onChange={(e) => setEditPlanForm({ ...editPlanForm, change_reason: e.target.value })}
                  />
                  <small className="text-muted">Opzionale, verrà salvato nello storico delle modifiche</small>
                </div>
              </div>
              <div className="modal-footer border-0">
                <button
                  className="btn btn-secondary"
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
                <button className="btn btn-primary" onClick={handleUpdateMealPlan} disabled={savingMealPlan}>
                  {savingMealPlan ? (
                    <><span className="spinner-border spinner-border-sm me-2"></span>Salvataggio...</>
                  ) : (
                    <><i className="ri-save-line me-2"></i>Salva Modifiche</>
                  )}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Version History Modal */}
      {showVersionsModal && selectedPlan && (
        <div className="modal show d-block" style={{ background: 'rgba(0,0,0,0.5)' }}>
          <div className="modal-dialog modal-dialog-centered modal-lg">
            <div className="modal-content">
              <div className="modal-header border-0" style={{ background: 'linear-gradient(135deg, rgba(107, 114, 128, 0.1) 0%, rgba(75, 85, 99, 0.1) 100%)' }}>
                <h5 className="modal-title">
                  <i className="ri-history-line me-2 text-secondary"></i>
                  Storico Modifiche
                </h5>
                <button className="btn-close" onClick={() => { setShowVersionsModal(false); setPlanVersions([]); }}></button>
              </div>
              <div className="modal-body">
                <div className="alert alert-secondary small mb-3">
                  <i className="ri-information-line me-1"></i>
                  Piano: <strong>{selectedPlan.name || 'Piano Alimentare'}</strong>
                </div>
                {loadingVersions ? (
                  <div className="text-center py-4">
                    <div className="spinner-border spinner-border-sm text-secondary" role="status"></div>
                    <small className="ms-2 text-muted">Caricamento storico...</small>
                  </div>
                ) : planVersions.length === 0 ? (
                  <p className="text-muted text-center py-3">
                    <i className="ri-information-line me-1"></i>
                    Nessuna modifica registrata per questo piano
                  </p>
                ) : (
                  <div className="table-responsive">
                    <table className="table table-sm table-hover mb-0" style={{ fontSize: '0.85rem' }}>
                      <thead>
                        <tr className="text-muted">
                          <th style={{ fontWeight: '500' }}>Versione</th>
                          <th style={{ fontWeight: '500' }}>Data Modifica</th>
                          <th style={{ fontWeight: '500' }}>Modificato da</th>
                          <th style={{ fontWeight: '500' }}>Periodo</th>
                          <th style={{ fontWeight: '500' }}>Motivo</th>
                          <th style={{ fontWeight: '500' }}>PDF</th>
                        </tr>
                      </thead>
                      <tbody>
                        {planVersions.map((version, idx) => (
                          <tr key={version.transaction_id || idx} className={version.is_current ? 'table-success' : ''}>
                            <td>
                              <span className="badge bg-secondary">v{version.version_number}</span>
                              {version.is_current && (
                                <span className="badge bg-success ms-1">Attuale</span>
                              )}
                            </td>
                            <td className="text-muted">
                              {version.changed_at ? new Date(version.changed_at).toLocaleString('it-IT', {
                                day: '2-digit', month: '2-digit', year: 'numeric',
                                hour: '2-digit', minute: '2-digit'
                              }) : '-'}
                            </td>
                            <td>{version.changed_by || '-'}</td>
                            <td className="text-muted">
                              {version.start_date ? new Date(version.start_date).toLocaleDateString('it-IT') : '-'}
                              {' → '}
                              {version.end_date ? new Date(version.end_date).toLocaleDateString('it-IT') : '-'}
                            </td>
                            <td className="text-muted" style={{ maxWidth: '200px' }}>
                              <span className="text-truncate d-inline-block" style={{ maxWidth: '200px' }} title={version.change_reason}>
                                {version.change_reason || '-'}
                              </span>
                            </td>
                            <td>
                              {version.has_file && version.piano_alimentare_file_path ? (
                                <a
                                  href={`/uploads/${version.piano_alimentare_file_path}`}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  className="btn btn-sm btn-outline-success py-0 px-2"
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
              <div className="modal-footer border-0">
                <button
                  className="btn btn-secondary"
                  onClick={() => { setShowVersionsModal(false); setPlanVersions([]); }}
                >
                  Chiudi
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Diario Entry Modal */}
      {showDiarioModal && (
        <div className="modal show d-block" style={{ background: 'rgba(0,0,0,0.5)' }}>
          <div className="modal-dialog modal-dialog-centered">
            <div className="modal-content">
              <div className="modal-header border-0" style={{ background: 'linear-gradient(135deg, rgba(236, 72, 153, 0.1) 0%, rgba(219, 39, 119, 0.1) 100%)' }}>
                <h5 className="modal-title">
                  <i className="ri-book-2-line me-2" style={{ color: '#ec4899' }}></i>
                  {diarioForm.id ? 'Modifica Nota' : 'Nuova Nota'}
                </h5>
                <button className="btn-close" onClick={() => setShowDiarioModal(false)}></button>
              </div>
              <div className="modal-body">
                <div className="mb-3">
                  <label className="form-label small text-muted">Data *</label>
                  <input
                    type="date"
                    className="form-control"
                    value={diarioForm.entry_date}
                    onChange={(e) => setDiarioForm({ ...diarioForm, entry_date: e.target.value })}
                  />
                </div>
                <div className="mb-3">
                  <label className="form-label small text-muted">Contenuto *</label>
                  <textarea
                    className="form-control"
                    rows="6"
                    placeholder="Scrivi qui la nota del diario...&#10;&#10;• Progressi osservati&#10;• Difficoltà riscontrate&#10;• Aggiustamenti al piano&#10;• Feedback del cliente"
                    value={diarioForm.content}
                    onChange={(e) => setDiarioForm({ ...diarioForm, content: e.target.value })}
                  ></textarea>
                </div>
              </div>
              <div className="modal-footer border-0">
                <button
                  className="btn btn-secondary"
                  onClick={() => {
                    setShowDiarioModal(false);
                    setDiarioForm({ id: null, entry_date: '', content: '' });
                  }}
                  disabled={savingDiario}
                >
                  Annulla
                </button>
                <button className="btn btn-primary" onClick={handleSaveDiarioEntry} disabled={savingDiario}>
                  {savingDiario ? (
                    <><span className="spinner-border spinner-border-sm me-2"></span>Salvataggio...</>
                  ) : (
                    <><i className="ri-save-line me-2"></i>Salva</>
                  )}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ==================== COACHING MODALS ==================== */}

      {/* Add Training Plan Modal */}
      {showAddTrainingPlanModal && (
        <div className="modal show d-block" style={{ background: 'rgba(0,0,0,0.5)' }}>
          <div className="modal-dialog modal-dialog-centered">
            <div className="modal-content">
              <div className="modal-header border-0" style={{ background: 'linear-gradient(135deg, rgba(245, 158, 11, 0.1) 0%, rgba(217, 119, 6, 0.1) 100%)' }}>
                <h5 className="modal-title">
                  <i className="ri-run-line me-2 text-warning"></i>
                  Nuovo Piano Allenamento
                </h5>
                <button className="btn-close" onClick={() => setShowAddTrainingPlanModal(false)}></button>
              </div>
              <div className="modal-body">
                <div className="mb-3">
                  <label className="form-label small text-muted">Nome Piano (opzionale)</label>
                  <input
                    type="text"
                    className="form-control"
                    placeholder="Es: Programma Forza Fase 1"
                    value={trainingPlanForm.name}
                    onChange={(e) => setTrainingPlanForm({ ...trainingPlanForm, name: e.target.value })}
                  />
                </div>
                <div className="row mb-3">
                  <div className="col-6">
                    <label className="form-label small text-muted">Data Inizio *</label>
                    <input
                      type="date"
                      className="form-control"
                      value={trainingPlanForm.start_date}
                      onChange={(e) => setTrainingPlanForm({ ...trainingPlanForm, start_date: e.target.value })}
                    />
                  </div>
                  <div className="col-6">
                    <label className="form-label small text-muted">Data Fine *</label>
                    <input
                      type="date"
                      className="form-control"
                      value={trainingPlanForm.end_date}
                      onChange={(e) => setTrainingPlanForm({ ...trainingPlanForm, end_date: e.target.value })}
                    />
                  </div>
                </div>
                <div className="mb-3">
                  <label className="form-label small text-muted">Piano Allenamento (PDF) *</label>
                  <input
                    type="file"
                    className="form-control"
                    accept=".pdf"
                    onChange={(e) => setTrainingPlanFile(e.target.files[0])}
                  />
                  <small className="text-muted">Carica il piano di allenamento in formato PDF (max 50MB)</small>
                </div>
                <div className="mb-3">
                  <label className="form-label small text-muted">Note (opzionale)</label>
                  <textarea
                    className="form-control"
                    rows="2"
                    placeholder="Note aggiuntive..."
                    value={trainingPlanForm.notes}
                    onChange={(e) => setTrainingPlanForm({ ...trainingPlanForm, notes: e.target.value })}
                  ></textarea>
                </div>
              </div>
              <div className="modal-footer border-0">
                <button
                  className="btn btn-secondary"
                  onClick={() => {
                    setShowAddTrainingPlanModal(false);
                    setTrainingPlanForm({ name: '', start_date: '', end_date: '', notes: '' });
                    setTrainingPlanFile(null);
                  }}
                  disabled={savingTrainingPlan}
                >
                  Annulla
                </button>
                <button className="btn btn-warning" onClick={handleAddTrainingPlan} disabled={savingTrainingPlan}>
                  {savingTrainingPlan ? (
                    <><span className="spinner-border spinner-border-sm me-2"></span>Salvataggio...</>
                  ) : (
                    <><i className="ri-save-line me-2"></i>Salva Piano</>
                  )}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Preview Training Plan PDF Modal */}
      {showPreviewTrainingModal && selectedTrainingPlan && (
        <div className="modal show d-block" style={{ background: 'rgba(0,0,0,0.5)' }} onClick={() => setShowPreviewTrainingModal(false)}>
          <div className="modal-dialog modal-dialog-centered modal-xl" onClick={(e) => e.stopPropagation()}>
            <div className="modal-content" style={{ height: '90vh' }}>
              <div className="modal-header border-0" style={{ background: 'linear-gradient(135deg, rgba(245, 158, 11, 0.1) 0%, rgba(217, 119, 6, 0.1) 100%)' }}>
                <h5 className="modal-title">
                  <i className="ri-file-pdf-line me-2 text-warning"></i>
                  {selectedTrainingPlan.name || 'Piano Allenamento'}
                </h5>
                <div className="d-flex gap-2 align-items-center">
                  <a
                    href={`/uploads/${selectedTrainingPlan.piano_allenamento_file_path}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="btn btn-sm btn-outline-warning"
                  >
                    <i className="ri-download-line me-1"></i>
                    Scarica
                  </a>
                  <button className="btn-close" onClick={() => setShowPreviewTrainingModal(false)}></button>
                </div>
              </div>
              <div className="modal-body p-0" style={{ height: 'calc(100% - 60px)' }}>
                <iframe
                  src={`/uploads/${selectedTrainingPlan.piano_allenamento_file_path}`}
                  style={{ width: '100%', height: '100%', border: 'none' }}
                  title="Piano Allenamento PDF"
                />
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Edit Training Plan Modal */}
      {showEditTrainingModal && selectedTrainingPlan && (
        <div className="modal show d-block" style={{ background: 'rgba(0,0,0,0.5)' }}>
          <div className="modal-dialog modal-dialog-centered">
            <div className="modal-content">
              <div className="modal-header border-0" style={{ background: 'linear-gradient(135deg, rgba(59, 130, 246, 0.1) 0%, rgba(37, 99, 235, 0.1) 100%)' }}>
                <h5 className="modal-title">
                  <i className="ri-edit-line me-2 text-primary"></i>
                  Modifica Piano Allenamento
                </h5>
                <button className="btn-close" onClick={() => setShowEditTrainingModal(false)}></button>
              </div>
              <div className="modal-body">
                <div className="alert alert-info small mb-3">
                  <i className="ri-information-line me-1"></i>
                  Stai modificando: <strong>{selectedTrainingPlan.name || 'Piano Allenamento'}</strong>
                </div>
                <div className="row mb-3">
                  <div className="col-6">
                    <label className="form-label small text-muted">Data Inizio *</label>
                    <input
                      type="date"
                      className="form-control"
                      value={editTrainingForm.start_date}
                      onChange={(e) => setEditTrainingForm({ ...editTrainingForm, start_date: e.target.value })}
                    />
                  </div>
                  <div className="col-6">
                    <label className="form-label small text-muted">Data Fine *</label>
                    <input
                      type="date"
                      className="form-control"
                      value={editTrainingForm.end_date}
                      onChange={(e) => setEditTrainingForm({ ...editTrainingForm, end_date: e.target.value })}
                    />
                  </div>
                </div>
                <div className="mb-3">
                  <label className="form-label small text-muted">Nuovo PDF (opzionale)</label>
                  <input
                    type="file"
                    className="form-control"
                    accept=".pdf"
                    onChange={(e) => setEditTrainingFile(e.target.files[0])}
                  />
                  <small className="text-muted">Lascia vuoto per mantenere il PDF esistente</small>
                </div>
                <div className="mb-3">
                  <label className="form-label small text-muted">Note (opzionale)</label>
                  <textarea
                    className="form-control"
                    rows="2"
                    placeholder="Note aggiuntive..."
                    value={editTrainingForm.notes}
                    onChange={(e) => setEditTrainingForm({ ...editTrainingForm, notes: e.target.value })}
                  ></textarea>
                </div>
                <div className="mb-3">
                  <label className="form-label small text-muted">Motivo della modifica</label>
                  <input
                    type="text"
                    className="form-control"
                    placeholder="Es: Aggiornamento esercizi fase intermedia"
                    value={editTrainingForm.change_reason}
                    onChange={(e) => setEditTrainingForm({ ...editTrainingForm, change_reason: e.target.value })}
                  />
                  <small className="text-muted">Opzionale, verrà salvato nello storico delle modifiche</small>
                </div>
              </div>
              <div className="modal-footer border-0">
                <button
                  className="btn btn-secondary"
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
                <button className="btn btn-primary" onClick={handleUpdateTrainingPlan} disabled={savingTrainingPlan}>
                  {savingTrainingPlan ? (
                    <><span className="spinner-border spinner-border-sm me-2"></span>Salvataggio...</>
                  ) : (
                    <><i className="ri-save-line me-2"></i>Salva Modifiche</>
                  )}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Training Plan Version History Modal */}
      {showTrainingVersionsModal && selectedTrainingPlan && (
        <div className="modal show d-block" style={{ background: 'rgba(0,0,0,0.5)' }}>
          <div className="modal-dialog modal-dialog-centered modal-lg">
            <div className="modal-content">
              <div className="modal-header border-0" style={{ background: 'linear-gradient(135deg, rgba(107, 114, 128, 0.1) 0%, rgba(75, 85, 99, 0.1) 100%)' }}>
                <h5 className="modal-title">
                  <i className="ri-history-line me-2 text-secondary"></i>
                  Storico Modifiche
                </h5>
                <button className="btn-close" onClick={() => { setShowTrainingVersionsModal(false); setTrainingVersions([]); }}></button>
              </div>
              <div className="modal-body">
                <div className="alert alert-secondary small mb-3">
                  <i className="ri-information-line me-1"></i>
                  Piano: <strong>{selectedTrainingPlan.name || 'Piano Allenamento'}</strong>
                </div>
                {loadingTrainingVersions ? (
                  <div className="text-center py-4">
                    <div className="spinner-border spinner-border-sm text-secondary" role="status"></div>
                    <small className="ms-2 text-muted">Caricamento storico...</small>
                  </div>
                ) : trainingVersions.length === 0 ? (
                  <p className="text-muted text-center py-3">
                    <i className="ri-information-line me-1"></i>
                    Nessuna modifica registrata per questo piano
                  </p>
                ) : (
                  <div className="table-responsive">
                    <table className="table table-sm table-hover mb-0" style={{ fontSize: '0.85rem' }}>
                      <thead>
                        <tr className="text-muted">
                          <th style={{ fontWeight: '500' }}>Versione</th>
                          <th style={{ fontWeight: '500' }}>Data Modifica</th>
                          <th style={{ fontWeight: '500' }}>Modificato da</th>
                          <th style={{ fontWeight: '500' }}>Periodo</th>
                          <th style={{ fontWeight: '500' }}>Motivo</th>
                          <th style={{ fontWeight: '500' }}>PDF</th>
                        </tr>
                      </thead>
                      <tbody>
                        {trainingVersions.map((version, idx) => (
                          <tr key={version.transaction_id || idx} className={version.is_current ? 'table-warning' : ''}>
                            <td>
                              <span className="badge bg-secondary">v{version.version_number}</span>
                              {version.is_current && (
                                <span className="badge bg-warning ms-1">Attuale</span>
                              )}
                            </td>
                            <td className="text-muted">
                              {version.changed_at ? new Date(version.changed_at).toLocaleString('it-IT', {
                                day: '2-digit', month: '2-digit', year: 'numeric',
                                hour: '2-digit', minute: '2-digit'
                              }) : '-'}
                            </td>
                            <td>{version.changed_by || '-'}</td>
                            <td className="text-muted">
                              {version.start_date ? new Date(version.start_date).toLocaleDateString('it-IT') : '-'}
                              {' → '}
                              {version.end_date ? new Date(version.end_date).toLocaleDateString('it-IT') : '-'}
                            </td>
                            <td className="text-muted" style={{ maxWidth: '200px' }}>
                              <span className="text-truncate d-inline-block" style={{ maxWidth: '200px' }} title={version.change_reason}>
                                {version.change_reason || '-'}
                              </span>
                            </td>
                            <td>
                              {version.has_file && version.piano_allenamento_file_path ? (
                                <a
                                  href={`/uploads/${version.piano_allenamento_file_path}`}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  className="btn btn-sm btn-outline-warning py-0 px-2"
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
              <div className="modal-footer border-0">
                <button
                  className="btn btn-secondary"
                  onClick={() => { setShowTrainingVersionsModal(false); setTrainingVersions([]); }}
                >
                  Chiudi
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Training Location Modal */}
      {showLocationModal && (
        <div className="modal show d-block" style={{ background: 'rgba(0,0,0,0.5)' }}>
          <div className="modal-dialog modal-dialog-centered">
            <div className="modal-content">
              <div className="modal-header border-0" style={{ background: 'linear-gradient(135deg, rgba(16, 185, 129, 0.1) 0%, rgba(5, 150, 105, 0.1) 100%)' }}>
                <h5 className="modal-title">
                  <i className="ri-map-pin-line me-2 text-success"></i>
                  {locationForm.id ? 'Modifica Luogo' : 'Nuovo Luogo di Allenamento'}
                </h5>
                <button className="btn-close" onClick={() => setShowLocationModal(false)}></button>
              </div>
              <div className="modal-body">
                <div className="mb-3">
                  <label className="form-label small text-muted">Luogo di Allenamento *</label>
                  <select
                    className="form-select"
                    value={locationForm.location}
                    onChange={(e) => setLocationForm({ ...locationForm, location: e.target.value })}
                  >
                    <option value="">Seleziona...</option>
                    <option value="casa">Casa</option>
                    <option value="palestra">Palestra</option>
                    <option value="ibrido">Ibrido</option>
                  </select>
                </div>
                <div className="row mb-3">
                  <div className="col-6">
                    <label className="form-label small text-muted">Data Inizio *</label>
                    <input
                      type="date"
                      className="form-control"
                      value={locationForm.start_date}
                      onChange={(e) => setLocationForm({ ...locationForm, start_date: e.target.value })}
                    />
                  </div>
                  <div className="col-6">
                    <label className="form-label small text-muted">Data Fine (opzionale)</label>
                    <input
                      type="date"
                      className="form-control"
                      value={locationForm.end_date}
                      onChange={(e) => setLocationForm({ ...locationForm, end_date: e.target.value })}
                    />
                    <small className="text-muted">Lascia vuoto se ancora in corso</small>
                  </div>
                </div>
                <div className="mb-3">
                  <label className="form-label small text-muted">Note (opzionale)</label>
                  <textarea
                    className="form-control"
                    rows="2"
                    placeholder="Note aggiuntive sul luogo..."
                    value={locationForm.notes}
                    onChange={(e) => setLocationForm({ ...locationForm, notes: e.target.value })}
                  ></textarea>
                </div>
                {locationForm.id && (
                  <div className="mb-3">
                    <label className="form-label small text-muted">Motivo della modifica</label>
                    <input
                      type="text"
                      className="form-control"
                      placeholder="Es: Cambio palestra, Inizio fase home training..."
                      value={locationForm.change_reason}
                      onChange={(e) => setLocationForm({ ...locationForm, change_reason: e.target.value })}
                    />
                  </div>
                )}
              </div>
              <div className="modal-footer border-0">
                <button
                  className="btn btn-secondary"
                  onClick={() => {
                    setShowLocationModal(false);
                    setLocationForm({ id: null, location: '', start_date: '', end_date: '', notes: '', change_reason: '' });
                  }}
                  disabled={savingLocation}
                >
                  Annulla
                </button>
                <button className="btn btn-success" onClick={handleSaveLocation} disabled={savingLocation}>
                  {savingLocation ? (
                    <><span className="spinner-border spinner-border-sm me-2"></span>Salvataggio...</>
                  ) : (
                    <><i className="ri-save-line me-2"></i>Salva</>
                  )}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Coaching Diario Entry Modal */}
      {showDiarioCoachingModal && (
        <div className="modal show d-block" style={{ background: 'rgba(0,0,0,0.5)' }}>
          <div className="modal-dialog modal-dialog-centered">
            <div className="modal-content">
              <div className="modal-header border-0" style={{ background: 'linear-gradient(135deg, rgba(245, 158, 11, 0.1) 0%, rgba(217, 119, 6, 0.1) 100%)' }}>
                <h5 className="modal-title">
                  <i className="ri-book-2-line me-2 text-warning"></i>
                  {diarioCoachingForm.id ? 'Modifica Nota Coaching' : 'Nuova Nota Coaching'}
                </h5>
                <button className="btn-close" onClick={() => setShowDiarioCoachingModal(false)}></button>
              </div>
              <div className="modal-body">
                <div className="mb-3">
                  <label className="form-label small text-muted">Data *</label>
                  <input
                    type="date"
                    className="form-control"
                    value={diarioCoachingForm.entry_date}
                    onChange={(e) => setDiarioCoachingForm({ ...diarioCoachingForm, entry_date: e.target.value })}
                  />
                </div>
                <div className="mb-3">
                  <label className="form-label small text-muted">Contenuto *</label>
                  <textarea
                    className="form-control"
                    rows="6"
                    placeholder="Scrivi qui la nota del diario coaching...&#10;&#10;• Progressi allenamento&#10;• Performance osservata&#10;• Aggiustamenti al piano&#10;• Feedback del cliente"
                    value={diarioCoachingForm.content}
                    onChange={(e) => setDiarioCoachingForm({ ...diarioCoachingForm, content: e.target.value })}
                  ></textarea>
                </div>
              </div>
              <div className="modal-footer border-0">
                <button
                  className="btn btn-secondary"
                  onClick={() => {
                    setShowDiarioCoachingModal(false);
                    setDiarioCoachingForm({ id: null, entry_date: '', content: '' });
                  }}
                  disabled={savingDiarioCoaching}
                >
                  Annulla
                </button>
                <button className="btn btn-warning" onClick={handleSaveDiarioCoaching} disabled={savingDiarioCoaching}>
                  {savingDiarioCoaching ? (
                    <><span className="spinner-border spinner-border-sm me-2"></span>Salvataggio...</>
                  ) : (
                    <><i className="ri-save-line me-2"></i>Salva</>
                  )}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Psicologia Diario Entry Modal */}
      {showDiarioPsicologiaModal && (
        <div className="modal show d-block" style={{ background: 'rgba(0,0,0,0.5)' }}>
          <div className="modal-dialog modal-dialog-centered">
            <div className="modal-content">
              <div className="modal-header border-0" style={{ background: 'linear-gradient(135deg, rgba(168, 85, 247, 0.1) 0%, rgba(124, 58, 237, 0.1) 100%)' }}>
                <h5 className="modal-title">
                  <i className="ri-book-2-line me-2" style={{ color: '#a855f7' }}></i>
                  {diarioPsicologiaForm.id ? 'Modifica Nota Psicologia' : 'Nuova Nota Psicologia'}
                </h5>
                <button className="btn-close" onClick={() => setShowDiarioPsicologiaModal(false)}></button>
              </div>
              <div className="modal-body">
                <div className="mb-3">
                  <label className="form-label small text-muted">Data *</label>
                  <input
                    type="date"
                    className="form-control"
                    value={diarioPsicologiaForm.entry_date}
                    onChange={(e) => setDiarioPsicologiaForm({ ...diarioPsicologiaForm, entry_date: e.target.value })}
                  />
                </div>
                <div className="mb-3">
                  <label className="form-label small text-muted">Contenuto *</label>
                  <textarea
                    className="form-control"
                    rows="6"
                    placeholder="Scrivi qui la nota del diario psicologia...&#10;&#10;• Progressi terapeutici&#10;• Osservazioni cliniche&#10;• Punti trattati nella seduta&#10;• Note per il prossimo incontro"
                    value={diarioPsicologiaForm.content}
                    onChange={(e) => setDiarioPsicologiaForm({ ...diarioPsicologiaForm, content: e.target.value })}
                  ></textarea>
                </div>
              </div>
              <div className="modal-footer border-0">
                <button
                  className="btn btn-secondary"
                  onClick={() => {
                    setShowDiarioPsicologiaModal(false);
                    setDiarioPsicologiaForm({ id: null, entry_date: '', content: '' });
                  }}
                  disabled={savingDiarioPsicologia}
                >
                  Annulla
                </button>
                <button className="btn" style={{ background: '#a855f7', color: 'white' }} onClick={handleSaveDiarioPsicologia} disabled={savingDiarioPsicologia}>
                  {savingDiarioPsicologia ? (
                    <><span className="spinner-border spinner-border-sm me-2"></span>Salvataggio...</>
                  ) : (
                    <><i className="ri-save-line me-2"></i>Salva</>
                  )}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Check Response Detail Modal */}
      {showCheckResponseModal && selectedCheckResponse && (
        <div className="modal show d-block" style={{ background: 'rgba(0,0,0,0.5)' }} onClick={() => setShowCheckResponseModal(false)}>
          <div className="modal-dialog modal-lg modal-dialog-centered modal-dialog-scrollable" onClick={(e) => e.stopPropagation()}>
            <div className="modal-content" style={{ borderRadius: '16px', overflow: 'hidden' }}>
              <div className="modal-header" style={{
                background: selectedCheckResponse.type === 'weekly' ? 'linear-gradient(135deg, #10b981 0%, #059669 100%)' :
                           selectedCheckResponse.type === 'dca' ? 'linear-gradient(135deg, #a855f7 0%, #9333ea 100%)' :
                           'linear-gradient(135deg, #f59e0b 0%, #d97706 100%)',
                color: 'white',
                border: 'none'
              }}>
                <h5 className="modal-title">
                  <i className={`me-2 ${selectedCheckResponse.type === 'weekly' ? 'ri-calendar-check-line' : selectedCheckResponse.type === 'dca' ? 'ri-heart-pulse-line' : 'ri-user-heart-line'}`}></i>
                  {selectedCheckResponse.type === 'weekly' ? 'Check Settimanale' : selectedCheckResponse.type === 'dca' ? 'Check Benessere' : 'Check Minori'}
                </h5>
                <button className="btn-close btn-close-white" onClick={() => setShowCheckResponseModal(false)}></button>
              </div>
              <div className="modal-body p-4">
                {loadingCheckDetail ? (
                  <div className="text-center py-5">
                    <div className="spinner-border text-primary" role="status"></div>
                    <p className="text-muted mt-3">Caricamento dettagli...</p>
                  </div>
                ) : (
                  <div>
                    {/* Header Info */}
                    <div className="d-flex justify-content-between align-items-center mb-4 pb-3 border-bottom">
                      <div>
                        <small className="text-muted">Data compilazione</small>
                        <p className="mb-0 fw-semibold">{selectedCheckResponse.submit_date}</p>
                      </div>
                      {selectedCheckResponse.type === 'weekly' && (
                        <div className="text-end">
                          <small className="text-muted">Peso</small>
                          <p className="mb-0 fw-semibold">{selectedCheckResponse.weight ? `${selectedCheckResponse.weight} kg` : <span className="text-muted">-</span>}</p>
                        </div>
                      )}
                    </div>

                    {/* Photos (for weekly check) */}
                    {selectedCheckResponse.type === 'weekly' && (
                      <div className="mb-4">
                        <h6 className="text-muted mb-3"><i className="ri-camera-line me-2"></i>Foto Progressi</h6>
                        <div className="row g-3">
                          <div className="col-4">
                            <div className="text-center">
                              <small className="text-muted d-block mb-2">Frontale</small>
                              {selectedCheckResponse.photo_front ? (
                                <img
                                  src={selectedCheckResponse.photo_front}
                                  alt="Foto frontale"
                                  className="img-fluid rounded"
                                  style={{ maxHeight: '150px', objectFit: 'cover', cursor: 'pointer' }}
                                  onClick={() => window.open(selectedCheckResponse.photo_front, '_blank')}
                                />
                              ) : (
                                <div className="p-4 rounded d-flex align-items-center justify-content-center" style={{ background: '#f8fafc', minHeight: '100px' }}>
                                  <span className="text-muted small">Non caricata</span>
                                </div>
                              )}
                            </div>
                          </div>
                          <div className="col-4">
                            <div className="text-center">
                              <small className="text-muted d-block mb-2">Laterale</small>
                              {selectedCheckResponse.photo_side ? (
                                <img
                                  src={selectedCheckResponse.photo_side}
                                  alt="Foto laterale"
                                  className="img-fluid rounded"
                                  style={{ maxHeight: '150px', objectFit: 'cover', cursor: 'pointer' }}
                                  onClick={() => window.open(selectedCheckResponse.photo_side, '_blank')}
                                />
                              ) : (
                                <div className="p-4 rounded d-flex align-items-center justify-content-center" style={{ background: '#f8fafc', minHeight: '100px' }}>
                                  <span className="text-muted small">Non caricata</span>
                                </div>
                              )}
                            </div>
                          </div>
                          <div className="col-4">
                            <div className="text-center">
                              <small className="text-muted d-block mb-2">Posteriore</small>
                              {selectedCheckResponse.photo_back ? (
                                <img
                                  src={selectedCheckResponse.photo_back}
                                  alt="Foto posteriore"
                                  className="img-fluid rounded"
                                  style={{ maxHeight: '150px', objectFit: 'cover', cursor: 'pointer' }}
                                  onClick={() => window.open(selectedCheckResponse.photo_back, '_blank')}
                                />
                              ) : (
                                <div className="p-4 rounded d-flex align-items-center justify-content-center" style={{ background: '#f8fafc', minHeight: '100px' }}>
                                  <span className="text-muted small">Non caricata</span>
                                </div>
                              )}
                            </div>
                          </div>
                        </div>
                      </div>
                    )}

                    {/* Ratings */}
                    {(selectedCheckResponse.nutritionist_rating || selectedCheckResponse.psychologist_rating ||
                      selectedCheckResponse.coach_rating || selectedCheckResponse.progress_rating) && (
                      <div className="mb-4">
                        <h6 className="text-muted mb-3"><i className="ri-star-line me-2"></i>Valutazioni Professionisti</h6>
                        <div className="row g-3">
                          {selectedCheckResponse.nutritionist_rating && (() => {
                            const nutriInfo = getWeeklySnapshotProfessional(selectedCheckResponse, 'nutritionist');
                            const nutri = nutriInfo?.assignment;
                            return (
                              <div className="col-6 col-md-3">
                                <div className="p-3 rounded text-center" style={{ background: '#dcfce7' }}>
                                  {nutri && (
                                    <div className="mb-2 d-flex justify-content-center">
                                      {nutri.avatar_path ? (
                                        <img src={nutri.avatar_path} alt="" className="rounded-circle" style={{ width: '40px', height: '40px', objectFit: 'cover', border: '2px solid #22c55e' }} />
                                      ) : (
                                        <div className="rounded-circle bg-success text-white d-flex align-items-center justify-content-center" style={{ width: '40px', height: '40px', fontSize: '0.75rem' }}>
                                          {nutri.professionista_nome?.split(' ').map(n => n[0]).join('').substring(0,2).toUpperCase() || '??'}
                                        </div>
                                      )}
                                    </div>
                                  )}
                                  <div className="fw-bold fs-4 text-success">{selectedCheckResponse.nutritionist_rating}</div>
                                  <small className="text-muted">{nutriInfo?.name || 'Nutrizionista'}</small>
                                </div>
                              </div>
                            );
                          })()}
                          {selectedCheckResponse.psychologist_rating && (() => {
                            const psicoInfo = getWeeklySnapshotProfessional(selectedCheckResponse, 'psychologist');
                            const psico = psicoInfo?.assignment;
                            return (
                              <div className="col-6 col-md-3">
                                <div className="p-3 rounded text-center" style={{ background: '#fef3c7' }}>
                                  {psico && (
                                    <div className="mb-2 d-flex justify-content-center">
                                      {psico.avatar_path ? (
                                        <img src={psico.avatar_path} alt="" className="rounded-circle" style={{ width: '40px', height: '40px', objectFit: 'cover', border: '2px solid #d97706' }} />
                                      ) : (
                                        <div className="rounded-circle text-white d-flex align-items-center justify-content-center" style={{ width: '40px', height: '40px', fontSize: '0.75rem', background: '#d97706' }}>
                                          {psico.professionista_nome?.split(' ').map(n => n[0]).join('').substring(0,2).toUpperCase() || '??'}
                                        </div>
                                      )}
                                    </div>
                                  )}
                                  <div className="fw-bold fs-4" style={{ color: '#d97706' }}>{selectedCheckResponse.psychologist_rating}</div>
                                  <small className="text-muted">{psicoInfo?.name || 'Psicologo/a'}</small>
                                </div>
                              </div>
                            );
                          })()}
                          {selectedCheckResponse.coach_rating && (() => {
                            const coachInfo = getWeeklySnapshotProfessional(selectedCheckResponse, 'coach');
                            const coach = coachInfo?.assignment;
                            return (
                              <div className="col-6 col-md-3">
                                <div className="p-3 rounded text-center" style={{ background: '#dbeafe' }}>
                                  {coach && (
                                    <div className="mb-2 d-flex justify-content-center">
                                      {coach.avatar_path ? (
                                        <img src={coach.avatar_path} alt="" className="rounded-circle" style={{ width: '40px', height: '40px', objectFit: 'cover', border: '2px solid #3b82f6' }} />
                                      ) : (
                                        <div className="rounded-circle bg-primary text-white d-flex align-items-center justify-content-center" style={{ width: '40px', height: '40px', fontSize: '0.75rem' }}>
                                          {coach.professionista_nome?.split(' ').map(n => n[0]).join('').substring(0,2).toUpperCase() || '??'}
                                        </div>
                                      )}
                                    </div>
                                  )}
                                  <div className="fw-bold fs-4 text-primary">{selectedCheckResponse.coach_rating}</div>
                                  <small className="text-muted">{coachInfo?.name || 'Coach'}</small>
                                </div>
                              </div>
                            );
                          })()}
                          {selectedCheckResponse.progress_rating && (
                            <div className="col-6 col-md-3">
                              <div className="p-3 rounded text-center" style={{ background: '#f3e8ff' }}>
                                <div className="mb-2 d-flex justify-content-center">
                                  <img
                                    src="/corposostenibile.jpg"
                                    alt="Corpo Sostenibile"
                                    className="rounded-circle"
                                    style={{ width: '40px', height: '40px', objectFit: 'cover', border: '2px solid #9333ea' }}
                                  />
                                </div>
                                <div className="fw-bold fs-4" style={{ color: '#9333ea' }}>{selectedCheckResponse.progress_rating}</div>
                                <small className="text-muted">Progresso</small>
                              </div>
                            </div>
                          )}
                        </div>
                      </div>
                    )}

                    {/* Wellness Ratings (for weekly check) */}
                    {selectedCheckResponse.type === 'weekly' && (
                      <div className="mb-4">
                        <h6 className="text-muted mb-3"><i className="ri-heart-pulse-line me-2"></i>Benessere</h6>
                        <div className="row g-2">
                          {[
                            { key: 'digestion_rating', label: 'Digestione', icon: '🍽️' },
                            { key: 'energy_rating', label: 'Energia', icon: '⚡' },
                            { key: 'strength_rating', label: 'Forza', icon: '💪' },
                            { key: 'hunger_rating', label: 'Fame', icon: '🍴' },
                            { key: 'sleep_rating', label: 'Sonno', icon: '😴' },
                            { key: 'mood_rating', label: 'Umore', icon: '😊' },
                            { key: 'motivation_rating', label: 'Motivazione', icon: '🔥' },
                          ].map(item => (
                            <div key={item.key} className="col-6 col-md-4">
                              <div className="d-flex align-items-center p-2 rounded" style={{ background: '#f8fafc' }}>
                                <span className="me-2">{item.icon}</span>
                                <span className="small text-muted me-auto">{item.label}</span>
                                <span className={`fw-semibold ${selectedCheckResponse[item.key] === null || selectedCheckResponse[item.key] === undefined ? 'text-muted' : ''}`}>
                                  {selectedCheckResponse[item.key] !== null && selectedCheckResponse[item.key] !== undefined ? `${selectedCheckResponse[item.key]}/10` : '-'}
                                </span>
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Professional Feedback (for weekly check) */}
                    {selectedCheckResponse.type === 'weekly' && (
                      <div className="mb-4">
                        <h6 className="text-muted mb-3"><i className="ri-feedback-line me-2"></i>Feedback Professionisti</h6>
                        <div className="row g-2">
                          <div className="col-12">
                            <div className="p-3 rounded" style={{ background: '#f0fdf4', border: '1px solid #bbf7d0' }}>
                              <small className="text-muted d-block mb-1">Feedback Nutrizionista</small>
                              <p className="mb-0 small">{selectedCheckResponse.nutritionist_feedback || <span className="text-muted fst-italic">Non compilato</span>}</p>
                            </div>
                          </div>
                          <div className="col-12">
                            <div className="p-3 rounded" style={{ background: '#fef3c7', border: '1px solid #fde68a' }}>
                              <small className="text-muted d-block mb-1">Feedback Psicologo</small>
                              <p className="mb-0 small">{selectedCheckResponse.psychologist_feedback || <span className="text-muted fst-italic">Non compilato</span>}</p>
                            </div>
                          </div>
                          <div className="col-12">
                            <div className="p-3 rounded" style={{ background: '#dbeafe', border: '1px solid #bfdbfe' }}>
                              <small className="text-muted d-block mb-1">Feedback Coach</small>
                              <p className="mb-0 small">{selectedCheckResponse.coach_feedback || <span className="text-muted fst-italic">Non compilato</span>}</p>
                            </div>
                          </div>
                        </div>
                      </div>
                    )}

                    {/* Programs Section (for weekly check) */}
                    {selectedCheckResponse.type === 'weekly' && (
                      <div className="mb-4">
                        <h6 className="text-muted mb-3"><i className="ri-calendar-check-line me-2"></i>Programmi</h6>
                        <div className="row g-2 align-items-start">
                          <div className="col-md-6 d-flex">
                            <div className="p-3 rounded flex-fill" style={{ background: '#f8fafc' }}>
                              <small className="text-muted d-block mb-1">Aderenza programma alimentare</small>
                              <p className="mb-0 small">{selectedCheckResponse.nutrition_program_adherence || <span className="text-muted fst-italic">Non compilato</span>}</p>
                            </div>
                          </div>
                          <div className="col-md-6 d-flex">
                            <div className="p-3 rounded flex-fill" style={{ background: '#f8fafc' }}>
                              <small className="text-muted d-block mb-1">Aderenza programma sportivo</small>
                              <p className="mb-0 small">{selectedCheckResponse.training_program_adherence || <span className="text-muted fst-italic">Non compilato</span>}</p>
                            </div>
                          </div>
                          <div className="col-12">
                            <div className="p-3 rounded" style={{ background: '#f8fafc' }}>
                              <small className="text-muted d-block mb-1">Esercizi modificati/aggiunti</small>
                              <p className="mb-0 small">{selectedCheckResponse.exercise_modifications || <span className="text-muted fst-italic">Non compilato</span>}</p>
                            </div>
                          </div>
                          <div className="col-md-4">
                            <div className="p-3 rounded text-center" style={{ background: '#f8fafc' }}>
                              <small className="text-muted d-block mb-1">Passi giornalieri</small>
                              <span className="fw-semibold">{selectedCheckResponse.daily_steps || <span className="text-muted">-</span>}</span>
                            </div>
                          </div>
                          <div className="col-md-4">
                            <div className="p-3 rounded text-center" style={{ background: '#f8fafc' }}>
                              <small className="text-muted d-block mb-1">Settimane completate</small>
                              <span className="fw-semibold">{selectedCheckResponse.completed_training_weeks || <span className="text-muted">-</span>}</span>
                            </div>
                          </div>
                          <div className="col-md-4">
                            <div className="p-3 rounded text-center" style={{ background: '#f8fafc' }}>
                              <small className="text-muted d-block mb-1">Giorni allenamento</small>
                              <span className="fw-semibold">{selectedCheckResponse.planned_training_days || <span className="text-muted">-</span>}</span>
                            </div>
                          </div>
                          <div className="col-12">
                            <div className="p-3 rounded" style={{ background: '#f8fafc' }}>
                              <small className="text-muted d-block mb-1">Tematiche live settimanali</small>
                              <p className="mb-0 small">{selectedCheckResponse.live_session_topics || <span className="text-muted fst-italic">Non compilato</span>}</p>
                            </div>
                          </div>
                        </div>
                      </div>
                    )}

                    {/* Text Fields - Reflections */}
                    <div className="mb-4">
                      <h6 className="text-muted mb-3"><i className="ri-lightbulb-line me-2"></i>Riflessioni</h6>
                      <div className="mb-3">
                        <div className="p-3 rounded" style={{ background: '#f0fdf4' }}>
                          <small className="text-muted d-block mb-1"><i className="ri-check-line me-1 text-success"></i>Cosa ha funzionato</small>
                          <p className="mb-0">{selectedCheckResponse.what_worked || <span className="text-muted fst-italic">Non compilato</span>}</p>
                        </div>
                      </div>
                      <div className="mb-3">
                        <div className="p-3 rounded" style={{ background: '#fef2f2' }}>
                          <small className="text-muted d-block mb-1"><i className="ri-close-line me-1 text-danger"></i>Cosa non ha funzionato</small>
                          <p className="mb-0">{selectedCheckResponse.what_didnt_work || <span className="text-muted fst-italic">Non compilato</span>}</p>
                        </div>
                      </div>
                      <div className="mb-3">
                        <div className="p-3 rounded" style={{ background: '#fffbeb' }}>
                          <small className="text-muted d-block mb-1"><i className="ri-lightbulb-line me-1 text-warning"></i>Cosa ho imparato</small>
                          <p className="mb-0">{selectedCheckResponse.what_learned || <span className="text-muted fst-italic">Non compilato</span>}</p>
                        </div>
                      </div>
                      <div className="mb-3">
                        <div className="p-3 rounded" style={{ background: '#eff6ff' }}>
                          <small className="text-muted d-block mb-1"><i className="ri-focus-line me-1 text-primary"></i>Focus prossima settimana</small>
                          <p className="mb-0">{selectedCheckResponse.what_focus_next || <span className="text-muted fst-italic">Non compilato</span>}</p>
                        </div>
                      </div>
                      {selectedCheckResponse.type === 'weekly' && (
                        <div className="mb-3">
                          <div className="p-3 rounded" style={{ background: '#fef2f2', border: '1px solid #fecaca' }}>
                            <small className="text-muted d-block mb-1"><i className="ri-first-aid-kit-line me-1 text-danger"></i>Infortuni / Note importanti</small>
                            <p className="mb-0">{selectedCheckResponse.injuries_notes || <span className="text-muted fst-italic">Nessun infortunio segnalato</span>}</p>
                          </div>
                        </div>
                      )}
                    </div>

                    {/* Referral (for weekly check) */}
                    {selectedCheckResponse.type === 'weekly' && (
                      <div className="mb-4">
                        <h6 className="text-muted mb-3"><i className="ri-user-add-line me-2"></i>Referral</h6>
                        <div className="p-3 rounded" style={{ background: '#f8fafc' }}>
                          <p className="mb-0">{selectedCheckResponse.referral || <span className="text-muted fst-italic">Nessun referral indicato</span>}</p>
                        </div>
                      </div>
                    )}

                    {/* Extra Comments */}
                    <div className="mb-3">
                      <h6 className="text-muted mb-2"><i className="ri-chat-1-line me-2"></i>Commenti extra</h6>
                      <div className="p-3 rounded" style={{ background: '#f8fafc' }}>
                        <p className="mb-0">{selectedCheckResponse.extra_comments || <span className="text-muted fst-italic">Nessun commento aggiuntivo</span>}</p>
                      </div>
                    </div>
                  </div>
                )}
              </div>
              <div className="modal-footer border-0">
                <button className="btn btn-secondary" onClick={() => setShowCheckResponseModal(false)}>
                  Chiudi
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
      {/* Modal Storico Diario */}
      {showDiaryHistoryModal && (
        <div className="modal fade show d-block" style={{ backgroundColor: 'rgba(0,0,0,0.5)' }} tabIndex="-1">
          <div className="modal-dialog modal-lg modal-dialog-centered">
            <div className="modal-content">
              <div className="modal-header">
                <h5 className="modal-title">Storico Modifiche</h5>
                <button type="button" className="btn-close" onClick={() => setShowDiaryHistoryModal(false)}></button>
              </div>
              <div className="modal-body">
                {loadingDiaryHistory ? (
                  <div className="text-center py-5">
                    <div className="spinner-border text-primary" role="status">
                      <span className="visually-hidden">Caricamento...</span>
                    </div>
                  </div>
                ) : diaryHistory.length === 0 ? (
                  <p className="text-muted text-center py-3">Nessuna modifica precedente trovata.</p>
                ) : (
                  <div className="list-group">
                    {diaryHistory.map((version, idx) => (
                      <div key={idx} className="list-group-item">
                        <div className="d-flex w-100 justify-content-between">
                          <small className="text-muted">
                            <i className="ri-time-line me-1"></i>
                            {version.modified_at}
                            <span className="mx-2">•</span>
                            <i className="ri-user-line me-1"></i>
                            {version.author}
                          </small>
                        </div>
                        <p className="mb-1 mt-2 small" style={{ whiteSpace: 'pre-wrap' }}>{version.content}</p>
                      </div>
                    ))}
                  </div>
                )}
              </div>
              <div className="modal-footer">
                <button type="button" className="btn btn-secondary" onClick={() => setShowDiaryHistoryModal(false)}>Chiudi</button>
              </div>
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
    </>
  );
}

export default ClientiDetail;

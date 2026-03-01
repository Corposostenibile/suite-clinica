import { useState, useEffect, useCallback } from 'react';
import { useOutletContext, useSearchParams } from 'react-router-dom';
import trainingService from '../../services/trainingService';
import teamService, {
    ROLE_LABELS,
    SPECIALTY_LABELS,
    SPECIALTY_FILTER_OPTIONS,
    ROLE_COLORS,
    SPECIALTY_COLORS
} from '../../services/teamService';
import GuidedTour from '../../components/GuidedTour';
import SupportWidget from '../../components/SupportWidget';
import {
    FaGraduationCap,
    FaChartBar,
    FaFilter,
    FaList,
    FaPlusCircle
} from 'react-icons/fa';
import './Formazione.css';

// Colori sfondo header card in base alla specializzazione (coerenti con TeamList)
const SPECIALTY_GRADIENTS = {
    nutrizione: 'linear-gradient(135deg, #22c55e 0%, #16a34a 100%)',
    nutrizionista: 'linear-gradient(135deg, #22c55e 0%, #16a34a 100%)',
    coach: 'linear-gradient(135deg, #f97316 0%, #ea580c 100%)',
    psicologia: 'linear-gradient(135deg, #ec4899 0%, #db2777 100%)',
    psicologo: 'linear-gradient(135deg, #ec4899 0%, #db2777 100%)',
};

const DEFAULT_GRADIENT = 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)';

// Tipi di training
const TRAINING_TYPES = {
    general: { label: 'Generale', color: '#6c757d', bg: 'secondary' },
    performance: { label: 'Performance', color: '#0d6efd', bg: 'primary' },
    progetto: { label: 'Progetto', color: '#198754', bg: 'success' },
    monthly: { label: 'Mensile', color: '#0dcaf0', bg: 'info' },
    annual: { label: 'Annuale', color: '#6f42c1', bg: 'purple' },
};

// Priorità richieste
const PRIORITIES = {
    low: { label: 'Bassa', color: '#0d6efd' },
    normal: { label: 'Normale', color: '#ffc107' },
    high: { label: 'Alta', color: '#fd7e14' },
    urgent: { label: 'Urgente', color: '#dc3545' },
};

function Formazione() {
    const { user } = useOutletContext();
    const isAdmin = Boolean(user?.is_admin === true || user?.role === 'admin' || user?.specialty === 'cco');
    const isTeamLeader = Boolean(user?.role === 'team_leader' && !isAdmin);
    const canManageTeamTraining = Boolean(isAdmin || isTeamLeader);
    const teamLeaderSpecialtyGroup = (() => {
        if (!isTeamLeader) return null;
        const s = String(user?.specialty || '').toLowerCase();
        if (s === 'nutrizione' || s === 'nutrizionista') return 'nutrizione';
        if (s === 'coach') return 'coach';
        if (s === 'psicologia' || s === 'psicologo') return 'psicologia';
        return null;
    })();
    const teamLeaderSpecialtyFilterValue = teamLeaderSpecialtyGroup === 'nutrizione'
        ? 'nutrizione,nutrizionista'
        : teamLeaderSpecialtyGroup === 'psicologia'
            ? 'psicologia,psicologo'
            : teamLeaderSpecialtyGroup || '';

    // ==================== ADMIN STATE ====================
    const [adminTab, setAdminTab] = useState('myTrainings'); // 'myTrainings' | 'team'
    const [adminView, setAdminView] = useState('professionals'); // 'professionals' | 'trainings' (for team view)
    const [professionals, setProfessionals] = useState([]);
    const [selectedProfessional, setSelectedProfessional] = useState(null);
    const [professionalTrainings, setProfessionalTrainings] = useState([]);
    const [adminFilters, setAdminFilters] = useState({ search: '', specialty: '' });
    const [currentPage, setCurrentPage] = useState(1);
    const ITEMS_PER_PAGE = 12;

    // ==================== USER STATE (used by both admin and normal users) ====================
    const [activeTab, setActiveTab] = useState('trainings');
    const [trainings, setTrainings] = useState([]);
    const [givenTrainings, setGivenTrainings] = useState([]); // Training erogati
    const [requests, setRequests] = useState([]);
    const [receivedRequests, setReceivedRequests] = useState([]); // Richieste ricevute
    const [recipients, setRecipients] = useState([]);
    
    // Configurazione Tour
    const [mostraTour, setMostraTour] = useState(false);
    const [searchParams] = useSearchParams();
    const deepLinkTrainingId = parseInt(searchParams.get('trainingId') || '', 10);
    const deepLinkTrainingTab = searchParams.get('trainingTab');

    // Effetto per avvio automatico tour da Hub Supporto
    useEffect(() => {
        if (searchParams.get('startTour') === 'true') {
            setMostraTour(true);
        }
    }, [searchParams]);
    
    const tourSteps = [
        {
            target: '[data-tour="header"]',
            title: 'Area Formazione',
            content: 'Qui puoi gestire il tuo percorso di crescita professionale, visualizzare i training assegnati e richiedere formazione specifica.',
            placement: 'bottom',
            icon: <FaGraduationCap size={18} color="white" />,
            iconBg: 'linear-gradient(135deg, #6366F1, #8B5CF6)'
        },
        {
            target: '[data-tour="stats-cards"]',
            title: 'Dashboard Rapida',
            content: 'Tieni d\'occhio le metriche principali: training ricevuti, erogati (se sei Team Leader) e lo stato delle tue richieste.',
            placement: 'bottom',
            icon: <FaChartBar size={18} color="white" />,
            iconBg: 'linear-gradient(135deg, #3B82F6, #60A5FA)'
        },
        {
            target: '[data-tour="tabs-navigation"]',
            title: 'Organizzazione',
            content: 'Usa i tab per navigare tra i training che ti sono stati assegnati, quelli che hai erogato e le richieste di formazione.',
            placement: 'bottom',
            icon: <FaFilter size={18} color="white" />,
            iconBg: 'linear-gradient(135deg, #F59E0B, #FBBF24)'
        },
        {
            target: '[data-tour="content-list"]',
            title: 'I Tuoi Training',
            content: 'Clicca su un elemento per espandere i dettagli, leggere il feedback e confermare la presa visione.',
            placement: 'top',
            icon: <FaList size={18} color="white" />,
            iconBg: 'linear-gradient(135deg, #10B981, #34D399)'
        },
        {
            target: '[data-tour="request-btn"]',
            title: 'Richiedi Formazione',
            content: 'Hai bisogno di supporto su un tema specifico? Invia una richiesta di training al tuo responsabile o a un collega esperto.',
            placement: 'left',
            icon: <FaPlusCircle size={18} color="white" />,
            iconBg: 'linear-gradient(135deg, #EC4899, #F472B6)'
        }
    ];

    // Paginazione per le 4 sezioni (10 elementi per pagina)
    const ITEMS_PER_SECTION = 10;
    const [trainingsPage, setTrainingsPage] = useState(1);
    const [givenTrainingsPage, setGivenTrainingsPage] = useState(1);
    const [requestsPage, setRequestsPage] = useState(1);
    const [receivedRequestsPage, setReceivedRequestsPage] = useState(1);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [expandedTraining, setExpandedTraining] = useState(null);
    const [expandedRequest, setExpandedRequest] = useState(null);
    const [showRequestModal, setShowRequestModal] = useState(false);
    const [showAckModal, setShowAckModal] = useState(null);
    const [ackNotes, setAckNotes] = useState('');
    const [newMessage, setNewMessage] = useState('');
    const [newRequest, setNewRequest] = useState({ subject: '', description: '', priority: 'normal', recipient_id: '' });
    const [actionLoading, setActionLoading] = useState(false);
    const [listSearch, setListSearch] = useState('');
    const [requestResponseDrafts, setRequestResponseDrafts] = useState({});
    const [requestResponseLoadingId, setRequestResponseLoadingId] = useState(null);

    // State per creare nuovo training
    const [showNewTrainingModal, setShowNewTrainingModal] = useState(false);
    const [newTraining, setNewTraining] = useState({
        title: '',
        content: '',
        review_type: 'feedback',
        strengths: '',
        improvements: '',
        goals: '',
        period_start: '',
        period_end: '',
    });

    // State per lazy loading
    const [recipientsLoaded, setRecipientsLoaded] = useState(false);
    const [recipientsLoading, setRecipientsLoading] = useState(false);
    const [teamLoaded, setTeamLoaded] = useState(false);
    const [teamLoading, setTeamLoading] = useState(false);

    // ==================== CALLBACK FUNCTIONS ====================
    const fetchData = useCallback(async () => {
        try {
            setLoading(true);
            setError(null);

            if (canManageTeamTraining) {
                // Admin: carica dati essenziali (NO recipients - lazy loaded)
                const [trainingsRes, givenRes, requestsRes, receivedRes] = await Promise.all([
                    trainingService.getMyTrainings(),
                    trainingService.getGivenTrainings(),
                    trainingService.getMyRequests(),
                    trainingService.getReceivedRequests(),
                ]);

                // Propri training ricevuti
                setTrainings(trainingsRes.trainings || []);
                // Training erogati ad altri
                setGivenTrainings(givenRes.trainings || []);
                // Richieste inviate
                setRequests(requestsRes.requests || []);
                // Richieste ricevute da altri
                setReceivedRequests(receivedRes.requests || []);
                // Recipients e Team Members saranno caricati lazy
            } else {
                // User normale: carica i propri training (NO recipients - lazy loaded)
                const [trainingsRes, requestsRes] = await Promise.all([
                    trainingService.getMyTrainings(),
                    trainingService.getMyRequests(),
                ]);

                setTrainings(trainingsRes.trainings || []);
                setRequests(requestsRes.requests || []);
            }
        } catch (err) {
            console.error('Errore caricamento dati:', err);
            setError(err.response?.data?.error || 'Errore nel caricamento dei dati');
        } finally {
            setLoading(false);
        }
    }, [canManageTeamTraining]);

    const loadRecipients = useCallback(async () => {
        if (recipientsLoaded || recipientsLoading) return;
        setRecipientsLoading(true);
        try {
            const recipientsRes = await trainingService.getRequestRecipients();
            setRecipients(recipientsRes.recipients || []);
            setRecipientsLoaded(true);
        } catch (err) {
            console.error('Errore caricamento recipients:', err);
        } finally {
            setRecipientsLoading(false);
        }
    }, [recipientsLoaded, recipientsLoading]);

    const loadTeamMembers = useCallback(async () => {
        if (teamLoaded || teamLoading) return;
        setTeamLoading(true);
        try {
            const teamRes = await teamService.getTeamMembers({ per_page: 5000, active: '1' });
            const members = (teamRes.members || []).filter(m => m.id !== user?.id);
            const mappedProfessionals = members.map(m => ({
                id: m.id,
                firstName: m.first_name,
                lastName: m.last_name,
                email: m.email,
                jobTitle: m.job_title || ROLE_LABELS[m.role] || '',
                department: SPECIALTY_LABELS[m.specialty] || m.department?.name || '',
                departmentId: m.department_id,
                role: m.role,
                specialty: m.specialty,
                avatarPath: m.avatar_path,
            }));
            setProfessionals(mappedProfessionals);
            setTeamLoaded(true);
        } catch (err) {
            console.error('Errore caricamento team:', err);
        } finally {
            setTeamLoading(false);
        }
    }, [teamLoaded, teamLoading, user?.id]);

    // ==================== EFFECTS ====================
    useEffect(() => {
        fetchData();
    }, [fetchData]);

    useEffect(() => {
        if (showRequestModal && !recipientsLoaded) {
            loadRecipients();
        }
    }, [showRequestModal, recipientsLoaded, loadRecipients]);

    useEffect(() => {
        if (adminTab === 'team' && canManageTeamTraining && !teamLoaded) {
            loadTeamMembers();
        }
    }, [adminTab, canManageTeamTraining, teamLoaded, loadTeamMembers]);

    useEffect(() => {
        if (!isTeamLeader || !teamLeaderSpecialtyFilterValue) return;
        setAdminFilters((prev) => (
            prev.specialty === teamLeaderSpecialtyFilterValue
                ? prev
                : { ...prev, specialty: teamLeaderSpecialtyFilterValue }
        ));
    }, [isTeamLeader, teamLeaderSpecialtyFilterValue]);

    useEffect(() => {
        if (!Number.isInteger(deepLinkTrainingId) || deepLinkTrainingId <= 0 || loading) {
            return;
        }

        const inTrainings = trainings.some(t => t.id === deepLinkTrainingId);
        const inGivenTrainings = givenTrainings.some(t => t.id === deepLinkTrainingId);

        let targetTab = deepLinkTrainingTab === 'given' ? 'given' : 'trainings';
        if (targetTab === 'given' && !inGivenTrainings && inTrainings) targetTab = 'trainings';
        if (targetTab === 'trainings' && !inTrainings && inGivenTrainings) targetTab = 'given';
        if (!inTrainings && !inGivenTrainings) return;

        if (activeTab !== targetTab) setActiveTab(targetTab);
        if (expandedTraining !== deepLinkTrainingId) setExpandedTraining(deepLinkTrainingId);
    }, [
        deepLinkTrainingId,
        deepLinkTrainingTab,
        loading,
        trainings,
        givenTrainings,
        activeTab,
        expandedTraining
    ]);

    // ==================== ADMIN FUNCTIONS ====================
    const handleSelectProfessional = async (professional) => {
        try {
            setLoading(true);
            setSelectedProfessional(professional);

            const res = await trainingService.getAdminUserTrainings(professional.id);
            setProfessionalTrainings(res.trainings || []);
            setAdminView('trainings');
        } catch (err) {
            console.error('Errore caricamento training:', err);
            alert(err.response?.data?.error || 'Errore nel caricamento dei training');
        } finally {
            setLoading(false);
        }
    };

    const handleBackToProfessionals = () => {
        setAdminView('professionals');
        setSelectedProfessional(null);
        setProfessionalTrainings([]);
        setExpandedTraining(null);
        setAdminTab('team'); // Torna al tab Gestione Team
    };

    const handleAdminFilterChange = (key, value) => {
        setAdminFilters(prev => ({ ...prev, [key]: value }));
        setCurrentPage(1); // Reset pagina quando cambiano i filtri
    };

    const resetAdminFilters = () => {
        setAdminFilters({
            search: '',
            specialty: isTeamLeader ? teamLeaderSpecialtyFilterValue : '',
        });
        setCurrentPage(1);
    };

    // Filtra professionisti per ricerca e specializzazione
    const filteredProfessionals = professionals.filter(p => {
        const searchLower = adminFilters.search.toLowerCase();
        const matchesSearch = !adminFilters.search || (
            p.firstName?.toLowerCase().includes(searchLower) ||
            p.lastName?.toLowerCase().includes(searchLower) ||
            p.email?.toLowerCase().includes(searchLower) ||
            p.department?.toLowerCase().includes(searchLower) ||
            p.jobTitle?.toLowerCase().includes(searchLower)
        );

        // Filtro per specializzazione (supporta valori multipli separati da virgola)
        const matchesSpecialty = !adminFilters.specialty ||
            adminFilters.specialty.split(',').some(spec => p.specialty === spec.trim());

        const isHM = p.specialty === 'health_manager' || p.role === 'health_manager';
        return matchesSearch && matchesSpecialty && !isHM;
    });

    // Paginazione
    const totalPages = Math.ceil(filteredProfessionals.length / ITEMS_PER_PAGE);
    const paginatedProfessionals = filteredProfessionals.slice(
        (currentPage - 1) * ITEMS_PER_PAGE,
        currentPage * ITEMS_PER_PAGE
    );

    // Stats per admin
    const adminStats = {
        total: professionals.length,
        nutrizione: professionals.filter(p => p.specialty === 'nutrizionista' || p.specialty === 'nutrizione').length,
        psicologia: professionals.filter(p => p.specialty === 'psicologo' || p.specialty === 'psicologia').length,
        coach: professionals.filter(p => p.specialty === 'coach').length,
    };
    const allowedSpecialtyFilterOptions = isTeamLeader && teamLeaderSpecialtyGroup
        ? SPECIALTY_FILTER_OPTIONS.filter((opt) => {
            const values = String(opt.value || '').split(',').map(v => v.trim());
            return values.includes(teamLeaderSpecialtyGroup);
        })
        : SPECIALTY_FILTER_OPTIONS;

    // ==================== USER FUNCTIONS ====================
    const stats = {
        // Training ricevuti
        totalTrainings: trainings.length,
        unacknowledged: trainings.filter(t => !t.isAcknowledged && !t.isDraft).length,
        unreadMessages: trainings.reduce((sum, t) => sum + (t.unreadCount || 0), 0),
        // Training erogati
        totalGiven: givenTrainings.length,
        givenPending: givenTrainings.filter(t => !t.isAcknowledged && !t.isDraft).length,
        givenAcknowledged: givenTrainings.filter(t => t.isAcknowledged).length,
        // Richieste inviate
        pendingRequests: requests.filter(r => r.status === 'pending').length,
        acceptedRequests: requests.filter(r => r.status === 'accepted').length,
        completedRequests: requests.filter(r => r.status === 'completed').length,
        rejectedRequests: requests.filter(r => r.status === 'rejected').length,
        // Richieste ricevute
        receivedPending: receivedRequests.filter(r => r.status === 'pending').length,
        receivedAccepted: receivedRequests.filter(r => r.status === 'accepted').length,
        receivedTotal: receivedRequests.length,
    };

    const normalizedSearch = listSearch.trim().toLowerCase();
    const filterBySearch = (value) => (value || '').toLowerCase().includes(normalizedSearch);

    const filteredTrainings = trainings.filter((t) => {
        if (!normalizedSearch) return true;
        return (
            filterBySearch(t.title) ||
            filterBySearch(t.content) ||
            filterBySearch(t.reviewType) ||
            filterBySearch(`${t.reviewer?.firstName || ''} ${t.reviewer?.lastName || ''}`)
        );
    });

    const filteredGivenTrainings = givenTrainings.filter((t) => {
        if (!normalizedSearch) return true;
        return (
            filterBySearch(t.title) ||
            filterBySearch(t.content) ||
            filterBySearch(t.reviewType) ||
            filterBySearch(`${t.reviewee?.firstName || ''} ${t.reviewee?.lastName || ''}`)
        );
    });

    const filteredRequests = requests.filter((r) => {
        if (!normalizedSearch) return true;
        return (
            filterBySearch(r.subject) ||
            filterBySearch(r.description) ||
            filterBySearch(r.priority) ||
            filterBySearch(r.status) ||
            filterBySearch(`${r.requestedTo?.firstName || ''} ${r.requestedTo?.lastName || ''}`)
        );
    });

    const filteredReceivedRequests = receivedRequests.filter((r) => {
        if (!normalizedSearch) return true;
        return (
            filterBySearch(r.subject) ||
            filterBySearch(r.description) ||
            filterBySearch(r.priority) ||
            filterBySearch(r.status) ||
            filterBySearch(`${r.requester?.firstName || ''} ${r.requester?.lastName || ''}`)
        );
    });

    const formatDate = (dateStr) => {
        if (!dateStr) return '-';
        const date = new Date(dateStr);
        const now = new Date();
        const diffDays = Math.floor((now - date) / (1000 * 60 * 60 * 24));

        if (diffDays === 0) return 'Oggi';
        if (diffDays === 1) return 'Ieri';
        if (diffDays < 7) return `${diffDays} giorni fa`;

        return date.toLocaleDateString('it-IT', { day: 'numeric', month: 'short', year: 'numeric' });
    };

    const formatDateTime = (dateStr) => {
        if (!dateStr) return '-';
        const date = new Date(dateStr);
        return date.toLocaleDateString('it-IT', {
            day: 'numeric',
            month: 'short',
            year: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });
    };

    const handleAcknowledge = async (trainingId) => {
        try {
            setActionLoading(true);
            await trainingService.acknowledgeTraining(trainingId, ackNotes);

            setTrainings(prev => prev.map(t =>
                t.id === trainingId
                    ? {
                        ...t,
                        isAcknowledged: true,
                        acknowledgedAt: new Date().toISOString(),
                        acknowledgmentNotes: ackNotes
                    }
                    : t
            ));
            setShowAckModal(null);
            setAckNotes('');
        } catch (err) {
            console.error('Errore conferma:', err);
            alert(err.response?.data?.error || 'Errore nella conferma del training');
        } finally {
            setActionLoading(false);
        }
    };

    const handleSendMessage = async (trainingId) => {
        if (!newMessage.trim()) return;

        try {
            setActionLoading(true);
            const response = await trainingService.sendMessage(trainingId, newMessage);

            if (response.success && response.message) {
                setTrainings(prev => prev.map(t =>
                    t.id === trainingId
                        ? {
                            ...t,
                            messages: [
                                ...(t.messages || []),
                                {
                                    id: response.message.id,
                                    senderId: response.message.senderId,
                                    senderName: response.message.senderName,
                                    content: response.message.content,
                                    createdAt: response.message.createdAt,
                                    isOwn: true,
                                }
                            ]
                        }
                        : t
                ));
            }
            setNewMessage('');
        } catch (err) {
            console.error('Errore invio messaggio:', err);
            alert(err.response?.data?.error || 'Errore nell\'invio del messaggio');
        } finally {
            setActionLoading(false);
        }
    };

    const handleCreateRequest = async () => {
        if (!newRequest.subject.trim()) return;
        if (!newRequest.recipient_id) {
            alert('Seleziona un destinatario');
            return;
        }

        try {
            setActionLoading(true);
            const response = await trainingService.createRequest({
                subject: newRequest.subject,
                description: newRequest.description,
                priority: newRequest.priority,
                recipient_id: parseInt(newRequest.recipient_id),
            });

            if (response.success) {
                const requestsRes = await trainingService.getMyRequests();
                setRequests(requestsRes.requests || []);

                setNewRequest({ subject: '', description: '', priority: 'normal', recipient_id: '' });
                setShowRequestModal(false);
                setActiveTab('requests');
            }
        } catch (err) {
            console.error('Errore creazione richiesta:', err);
            alert(err.response?.data?.error || 'Errore nella creazione della richiesta');
        } finally {
            setActionLoading(false);
        }
    };

    const handleCancelRequest = async (requestId) => {
        if (!window.confirm('Sei sicuro di voler cancellare questa richiesta?')) return;

        try {
            setActionLoading(true);
            await trainingService.cancelRequest(requestId);
            setRequests(prev => prev.filter(r => r.id !== requestId));
        } catch (err) {
            console.error('Errore cancellazione:', err);
            alert(err.response?.data?.error || 'Errore nella cancellazione della richiesta');
        } finally {
            setActionLoading(false);
        }
    };

    const handleRespondToReceivedRequest = async (request, action) => {
        if (!request?.id) return;
        if (!['accept', 'reject'].includes(action)) return;

        try {
            setRequestResponseLoadingId(request.id);
            const responseNotes = (requestResponseDrafts[request.id] || '').trim();
            const res = await trainingService.respondToRequest(request.id, {
                action,
                response_notes: responseNotes,
            });

            if (res?.success) {
                setReceivedRequests(prev => prev.map(r => (
                    r.id === request.id
                        ? {
                            ...r,
                            status: res.request?.status || (action === 'accept' ? 'accepted' : 'rejected'),
                            respondedAt: res.request?.respondedAt || new Date().toISOString(),
                            responseNotes: res.request?.responseNotes ?? responseNotes,
                            reviewId: res.request?.reviewId ?? r.reviewId,
                        }
                        : r
                )));
            }
        } catch (err) {
            console.error('Errore risposta richiesta:', err);
            alert(err.response?.data?.message || err.response?.data?.error || 'Errore nella gestione della richiesta');
        } finally {
            setRequestResponseLoadingId(null);
        }
    };

    const handleOpenTrainingFromRequest = async (request) => {
        if (!canManageTeamTraining || !request?.requester?.id) return;

        try {
            setActionLoading(true);
            const prof = {
                id: request.requester.id,
                firstName: request.requester.firstName || '',
                lastName: request.requester.lastName || '',
            };
            setSelectedProfessional(prof);

            const res = await trainingService.getAdminUserTrainings(request.requester.id);
            setProfessionalTrainings(res.trainings || []);
            setAdminView('trainings');
            setAdminTab('team');

            setNewTraining(prev => ({
                ...prev,
                title: prev.title?.trim() ? prev.title : `Training: ${request.subject || 'Richiesta Formazione'}`,
                content: prev.content?.trim() ? prev.content : (request.description || ''),
            }));
            setShowNewTrainingModal(true);
        } catch (err) {
            console.error('Errore apertura scrittura training da richiesta:', err);
            alert(err.response?.data?.error || 'Errore nel caricamento dei training del professionista');
        } finally {
            setActionLoading(false);
        }
    };

    const handleCreateTraining = async () => {
        if (!newTraining.title.trim()) {
            alert('Inserisci un titolo');
            return;
        }
        if (!newTraining.content.trim()) {
            alert('Inserisci il contenuto del training');
            return;
        }
        if (!selectedProfessional?.id) {
            alert('Nessun professionista selezionato');
            return;
        }

        try {
            setActionLoading(true);
            const response = await trainingService.createTrainingForUser(selectedProfessional.id, {
                title: newTraining.title,
                content: newTraining.content,
                review_type: newTraining.review_type,
                strengths: newTraining.strengths,
                improvements: newTraining.improvements,
                goals: newTraining.goals,
                period_start: newTraining.period_start || null,
                period_end: newTraining.period_end || null,
            });

            if (response.success) {
                // Ricarica i training del professionista
                const res = await trainingService.getAdminUserTrainings(selectedProfessional.id);
                setProfessionalTrainings(res.trainings || []);

                // Resetta il form e chiudi il modal
                setNewTraining({
                    title: '',
                    content: '',
                    review_type: 'feedback',
                    strengths: '',
                    improvements: '',
                    goals: '',
                    period_start: '',
                    period_end: '',
                });
                setShowNewTrainingModal(false);
            }
        } catch (err) {
            console.error('Errore creazione training:', err);
            alert(err.response?.data?.error || 'Errore nella creazione del training');
        } finally {
            setActionLoading(false);
        }
    };

    const handleMarkAllRead = async (trainingId) => {
        try {
            await trainingService.markAllMessagesRead(trainingId);
            setTrainings(prev => prev.map(t =>
                t.id === trainingId
                    ? { ...t, unreadCount: 0 }
                    : t
            ));
        } catch (err) {
            console.error('Errore mark all read:', err);
        }
    };

    useEffect(() => {
        if (expandedTraining && !isAdmin) {
            const training = trainings.find(t => t.id === expandedTraining);
            if (training && training.unreadCount > 0) {
                handleMarkAllRead(expandedTraining);
            }
        }
    }, [expandedTraining, trainings, isAdmin]);

    // ==================== RENDER ====================
    if (loading) {
        return (
            <div className="d-flex justify-content-center align-items-center" style={{ minHeight: '400px' }}>
                <div className="spinner-border text-primary" role="status">
                    <span className="visually-hidden">Caricamento...</span>
                </div>
            </div>
        );
    }

    if (error) {
        return (
            <div className="d-flex flex-column justify-content-center align-items-center" style={{ minHeight: '400px' }}>
                <i className="ri-error-warning-line text-danger" style={{ fontSize: '64px' }}></i>
                <h5 className="mt-3 mb-1">Errore</h5>
                <p className="text-muted">{error}</p>
                <button className="btn btn-primary" onClick={fetchData}>
                    <i className="ri-refresh-line me-2"></i>
                    Riprova
                </button>
            </div>
        );
    }

    // ==================== ADMIN VIEW ====================
    if (canManageTeamTraining) {
        // Se stiamo visualizzando i training di un professionista specifico
        if (adminView === 'trainings' && selectedProfessional) {
            // Questo blocco viene gestito sotto
        } else {
            // Vista principale admin con tabs
            return (
                <div className="container-fluid p-0">
                    {/* Header */}
                    <div className="d-flex flex-wrap align-items-center justify-content-between mb-4" data-tour="header">
                        <div>
                            <h4 className="mb-1">Formazione</h4>
                            <p className="text-muted mb-0">
                                {stats.unacknowledged > 0
                                    ? `${stats.unacknowledged} training da confermare`
                                    : 'Gestione training e richieste di formazione'}
                            </p>
                        </div>
                    </div>

                    {/* Stats Row - KPI sui training */}
                    <div className="row g-3 mb-4" data-tour="stats-cards">
                        {[
                            { label: 'Training Ricevuti', value: stats.totalTrainings, icon: 'ri-book-open-line', color: '#3b82f6', badge: stats.unacknowledged > 0 ? stats.unacknowledged : null },
                            { label: 'Training Erogati', value: stats.totalGiven, icon: 'ri-presentation-line', color: '#22c55e', badge: stats.givenPending > 0 ? stats.givenPending : null },
                            { label: 'Richieste Ricevute', value: stats.receivedTotal, icon: 'ri-mail-download-line', color: '#0dcaf0', badge: stats.receivedPending > 0 ? stats.receivedPending : null },
                            { label: 'Richieste Inviate', value: requests.length, icon: 'ri-mail-send-line', color: '#f97316', badge: stats.pendingRequests > 0 ? stats.pendingRequests : null },
                        ].map((stat, idx) => (
                            <div key={idx} className="col-xl-3 col-sm-6">
                                <div className="welcome-kpi-card-sm">
                                    <div className="d-flex justify-content-between align-items-center">
                                        <div>
                                            <div className="kpi-label">{stat.label}</div>
                                            <div className="d-flex align-items-center gap-2">
                                                <div className="kpi-value">{stat.value}</div>
                                                {stat.badge && <span className="badge bg-danger">{stat.badge}</span>}
                                            </div>
                                        </div>
                                        <div className="kpi-icon" style={{ background: `${stat.color}15`, color: stat.color }}>
                                            <i className={`${stat.icon} fs-5`}></i>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        ))}
                    </div>

                    {/* Main Tabs AND Sub Tabs Navigation Wrapper for Tour */}
                    <div data-tour="tabs-navigation">
                        {/* Main Tabs: I Miei Training | Gestione Team */}
                        <div className="formazione-tabs mb-4">
                            <button
                                className={`formazione-tab${adminTab === 'myTrainings' ? ' active' : ''}`}
                                onClick={() => setAdminTab('myTrainings')}
                            >
                                <i className="ri-user-line"></i>
                                I Miei Training
                                {stats.unacknowledged > 0 && <span className="formazione-tab-badge danger">{stats.unacknowledged}</span>}
                            </button>
                            <button
                                className={`formazione-tab${adminTab === 'team' ? ' active' : ''}`}
                                onClick={() => setAdminTab('team')}
                            >
                                <i className="ri-team-line"></i>
                                Gestione Team
                                <span className="formazione-tab-count">{professionals.length}</span>
                            </button>
                        </div>

                        {/* Tab Content: I Miei Training - Included in Tour Highlight */}
                        {adminTab === 'myTrainings' && (
                            <>
                                {/* Sub-tabs for all training sections */}
                                <div className="card mb-4">
                                    <div className="card-header bg-white border-bottom">
                                        <div className="formazione-tabs formazione-subtabs">
                                            <button className={`formazione-tab${activeTab === 'trainings' ? ' active' : ''}`} onClick={() => setActiveTab('trainings')}>
                                                <i className="ri-book-open-line"></i>
                                                <span className="d-none d-sm-inline">Training </span>Ricevuti
                                                {stats.unacknowledged > 0 && <span className="formazione-tab-badge danger">{stats.unacknowledged}</span>}
                                            </button>
                                            <button className={`formazione-tab${activeTab === 'given' ? ' active' : ''}`} onClick={() => setActiveTab('given')}>
                                                <i className="ri-presentation-line"></i>
                                                <span className="d-none d-sm-inline">Training </span>Erogati
                                                {stats.givenPending > 0 && <span className="formazione-tab-badge warning">{stats.givenPending}</span>}
                                            </button>
                                            <button className={`formazione-tab${activeTab === 'received' ? ' active' : ''}`} onClick={() => setActiveTab('received')}>
                                                <i className="ri-mail-download-line"></i>
                                                <span className="d-none d-sm-inline">Richieste </span>Ricevute
                                                {stats.receivedPending > 0 && <span className="formazione-tab-badge info">{stats.receivedPending}</span>}
                                            </button>
                                        </div>
                                    </div>
                                    <div className="px-3 py-2 border-bottom bg-white">
                                        <div className="position-relative">
                                            <i className="ri-search-line position-absolute text-muted" style={{ left: '12px', top: '50%', transform: 'translateY(-50%)' }}></i>
                                            <input
                                                type="text"
                                                className="form-control bg-light border-0"
                                                placeholder="Cerca training/richieste..."
                                                value={listSearch}
                                                onChange={(e) => {
                                                    setTrainingsPage(1);
                                                    setGivenTrainingsPage(1);
                                                    setRequestsPage(1);
                                                    setReceivedRequestsPage(1);
                                                    setListSearch(e.target.value);
                                                }}
                                                style={{ paddingLeft: '36px' }}
                                            />
                                        </div>
                                    </div>


                                <div className="card-body p-0">
                                    {/* Training List */}
                                    {activeTab === 'trainings' && (
                                        <div data-tour="content-list">
                                            {filteredTrainings.length === 0 ? (
                                                <div className="text-center py-5">
                                                    <i className="ri-book-open-line text-muted" style={{ fontSize: '64px' }}></i>
                                                    <h5 className="mt-3 mb-1">Nessun training</h5>
                                                    <p className="text-muted">Non hai ancora ricevuto training.</p>
                                                </div>
                                            ) : (
                                                filteredTrainings.slice((trainingsPage - 1) * ITEMS_PER_SECTION, trainingsPage * ITEMS_PER_SECTION).map(training => (
                                                    <div key={training.id} className="border-bottom">
                                                        <div
                                                            className="p-3 d-flex justify-content-between align-items-start"
                                                            style={{ cursor: 'pointer', background: expandedTraining === training.id ? '#f8f9fa' : 'white' }}
                                                            onClick={() => setExpandedTraining(expandedTraining === training.id ? null : training.id)}
                                                        >
                                                            <div className="flex-grow-1">
                                                                <div className="d-flex align-items-center gap-2 mb-1">
                                                                    <h6 className="mb-0">{training.title}</h6>
                                                                    <i className={`ri-arrow-${expandedTraining === training.id ? 'up' : 'down'}-s-line`}></i>
                                                                </div>
                                                                <div className="d-flex flex-wrap gap-2 align-items-center text-muted small">
                                                                    <span><i className="ri-user-line me-1"></i>{training.reviewer?.firstName} {training.reviewer?.lastName}</span>
                                                                    <span><i className="ri-calendar-line me-1"></i>{formatDate(training.createdAt)}</span>
                                                                </div>
                                                            </div>
                                                            <div className="d-flex gap-2 flex-wrap justify-content-end">
                                                                <span className="badge" style={{ background: `${TRAINING_TYPES[training.reviewType]?.color || '#6c757d'}20`, color: TRAINING_TYPES[training.reviewType]?.color || '#6c757d' }}>
                                                                    {TRAINING_TYPES[training.reviewType]?.label || training.reviewType}
                                                                </span>
                                                                {training.isAcknowledged ? (
                                                                    <span className="badge bg-success"><i className="ri-check-line me-1"></i>Confermato</span>
                                                                ) : (
                                                                    <span className="badge bg-warning text-dark">Da confermare</span>
                                                                )}
                                                                {training.unreadCount > 0 && (
                                                                    <span className="badge bg-danger"><i className="ri-message-3-line me-1"></i>{training.unreadCount}</span>
                                                                )}
                                                            </div>
                                                        </div>

                                                        {expandedTraining === training.id && (
                                                            <div className="p-4 bg-light border-top">
                                                                {(training.periodStart || training.periodEnd) && (
                                                                    <p className="text-muted small mb-3">
                                                                        <i className="ri-calendar-2-line me-1"></i>
                                                                        Periodo: {training.periodStart || '-'} - {training.periodEnd || '-'}
                                                                    </p>
                                                                )}
                                                                <div className="bg-white rounded p-3 mb-3">
                                                                    <p style={{ whiteSpace: 'pre-line' }}>{training.content}</p>
                                                                </div>
                                                                {training.strengths && (
                                                                    <div className="rounded p-3 mb-3" style={{ background: '#d1fae5', borderLeft: '4px solid #10b981' }}>
                                                                        <h6 className="text-success mb-2"><i className="ri-thumb-up-line me-2"></i>Punti di Forza</h6>
                                                                        <p className="mb-0" style={{ whiteSpace: 'pre-line' }}>{training.strengths}</p>
                                                                    </div>
                                                                )}
                                                                {training.improvements && (
                                                                    <div className="rounded p-3 mb-3" style={{ background: '#fef3c7', borderLeft: '4px solid #f59e0b' }}>
                                                                        <h6 className="text-warning mb-2"><i className="ri-lightbulb-line me-2"></i>Aree di Miglioramento</h6>
                                                                        <p className="mb-0" style={{ whiteSpace: 'pre-line' }}>{training.improvements}</p>
                                                                    </div>
                                                                )}
                                                                {training.goals && (
                                                                    <div className="rounded p-3 mb-3" style={{ background: '#dbeafe', borderLeft: '4px solid #3b82f6' }}>
                                                                        <h6 className="text-primary mb-2"><i className="ri-focus-3-line me-2"></i>Obiettivi</h6>
                                                                        <p className="mb-0" style={{ whiteSpace: 'pre-line' }}>{training.goals}</p>
                                                                    </div>
                                                                )}

                                                                {training.isAcknowledged ? (
                                                                    <div className="alert alert-success mb-3">
                                                                        <div className="d-flex align-items-center">
                                                                            <i className="ri-check-double-line fs-4 me-2"></i>
                                                                            <div>
                                                                                <strong>Confermato</strong>
                                                                                <span className="ms-2 text-muted small">il {formatDateTime(training.acknowledgedAt)}</span>
                                                                                {training.acknowledgmentNotes && <p className="mb-0 mt-1 small">{training.acknowledgmentNotes}</p>}
                                                                            </div>
                                                                        </div>
                                                                    </div>
                                                                ) : (
                                                                    <div className="alert alert-warning mb-3">
                                                                        <div className="d-flex align-items-center justify-content-between flex-wrap gap-2">
                                                                            <div>
                                                                                <i className="ri-information-line me-2"></i>
                                                                                <strong>Conferma di aver letto questo training</strong>
                                                                            </div>
                                                                            <button className="btn btn-success btn-sm" onClick={(e) => { e.stopPropagation(); setShowAckModal(training.id); }} disabled={actionLoading}>
                                                                                <i className="ri-check-line me-1"></i>Conferma Lettura
                                                                            </button>
                                                                        </div>
                                                                    </div>
                                                                )}

                                                                <div className="bg-white rounded p-3">
                                                                    <h6 className="mb-3"><i className="ri-chat-3-line me-2"></i>Discussione</h6>
                                                                    <div className="mb-3" style={{ maxHeight: '300px', overflowY: 'auto', minHeight: (training.messages?.length || 0) > 0 ? '100px' : '0' }}>
                                                                        {(!training.messages || training.messages.length === 0) ? (
                                                                            <p className="text-muted small text-center py-3">Nessun messaggio. Inizia la discussione!</p>
                                                                        ) : (
                                                                            training.messages.map(msg => (
                                                                                <div key={msg.id} className={`p-2 rounded mb-2 ${msg.isOwn ? 'ms-5' : 'me-5'}`} style={{ background: msg.isOwn ? '#e3f2fd' : '#f5f5f5' }}>
                                                                                    <div className="d-flex justify-content-between mb-1">
                                                                                        <strong className="small">{msg.senderName}</strong>
                                                                                        <span className="text-muted small">{formatDate(msg.createdAt)}</span>
                                                                                    </div>
                                                                                    <p className="mb-0 small">{msg.content}</p>
                                                                                </div>
                                                                            ))
                                                                        )}
                                                                    </div>
                                                                    <div className="input-group">
                                                                        <input type="text" className="form-control" placeholder="Scrivi un messaggio..." value={newMessage}
                                                                            onChange={(e) => setNewMessage(e.target.value)}
                                                                            onKeyPress={(e) => { if (e.key === 'Enter' && !actionLoading) handleSendMessage(training.id); }}
                                                                            onClick={(e) => e.stopPropagation()} disabled={actionLoading} />
                                                                        <button className="btn btn-primary" onClick={(e) => { e.stopPropagation(); handleSendMessage(training.id); }} disabled={actionLoading || !newMessage.trim()}>
                                                                            {actionLoading ? <span className="spinner-border spinner-border-sm"></span> : <i className="ri-send-plane-line"></i>}
                                                                        </button>
                                                                    </div>
                                                                </div>
                                                            </div>
                                                        )}
                                                    </div>
                                                ))
                                            )}
                                            {/* Paginazione Training Ricevuti */}
                                            {filteredTrainings.length > ITEMS_PER_SECTION && (() => {
                                                const tp = Math.ceil(filteredTrainings.length / ITEMS_PER_SECTION);
                                                return (
                                                <div className="form-pagination">
                                                    <span className="form-pagination-info">
                                                        {Math.min((trainingsPage - 1) * ITEMS_PER_SECTION + 1, filteredTrainings.length)}-{Math.min(trainingsPage * ITEMS_PER_SECTION, filteredTrainings.length)} di {filteredTrainings.length}
                                                    </span>
                                                    <div className="form-pagination-buttons">
                                                        <button className="form-page-btn" disabled={trainingsPage === 1} onClick={() => setTrainingsPage(p => Math.max(1, p - 1))}>&laquo;</button>
                                                        {Array.from({ length: tp }, (_, i) => i + 1)
                                                            .filter(p => p >= Math.max(1, trainingsPage - 2) && p <= Math.min(tp, trainingsPage + 2))
                                                            .map(p => (
                                                                <button key={p} className={`form-page-btn${trainingsPage === p ? ' active' : ''}`} onClick={() => setTrainingsPage(p)}>{p}</button>
                                                            ))}
                                                        <button className="form-page-btn" disabled={trainingsPage >= tp} onClick={() => setTrainingsPage(p => Math.min(tp, p + 1))}>&raquo;</button>
                                                    </div>
                                                </div>
                                                );
                                            })()}
                                        </div>
                                    )}

                                    {/* Given Trainings List - Training Erogati */}
                                    {activeTab === 'given' && (
                                        <div>
                                            {filteredGivenTrainings.length === 0 ? (
                                                <div className="text-center py-5">
                                                    <i className="ri-presentation-line text-muted" style={{ fontSize: '64px' }}></i>
                                                    <h5 className="mt-3 mb-1">Nessun training erogato</h5>
                                                    <p className="text-muted">Non hai ancora erogato training ad altri.</p>
                                                </div>
                                            ) : (
                                                filteredGivenTrainings.slice((givenTrainingsPage - 1) * ITEMS_PER_SECTION, givenTrainingsPage * ITEMS_PER_SECTION).map(training => (
                                                    <div key={training.id} className="border-bottom">
                                                        <div
                                                            className="p-3 d-flex justify-content-between align-items-start"
                                                            style={{ cursor: 'pointer', background: expandedTraining === training.id ? '#f8f9fa' : 'white' }}
                                                            onClick={() => setExpandedTraining(expandedTraining === training.id ? null : training.id)}
                                                        >
                                                            <div className="flex-grow-1">
                                                                <div className="d-flex align-items-center gap-2 mb-1">
                                                                    <h6 className="mb-0">{training.title}</h6>
                                                                    <i className={`ri-arrow-${expandedTraining === training.id ? 'up' : 'down'}-s-line`}></i>
                                                                </div>
                                                                <div className="d-flex flex-wrap gap-2 align-items-center text-muted small">
                                                                    <span><i className="ri-user-received-line me-1"></i>A: {training.reviewee?.firstName} {training.reviewee?.lastName}</span>
                                                                    <span><i className="ri-calendar-line me-1"></i>{formatDate(training.createdAt)}</span>
                                                                </div>
                                                            </div>
                                                            <div className="d-flex gap-2 flex-wrap justify-content-end">
                                                                <span className="badge" style={{ background: `${TRAINING_TYPES[training.reviewType]?.color || '#6c757d'}20`, color: TRAINING_TYPES[training.reviewType]?.color || '#6c757d' }}>
                                                                    {TRAINING_TYPES[training.reviewType]?.label || training.reviewType}
                                                                </span>
                                                                {training.isDraft ? (
                                                                    <span className="badge bg-secondary"><i className="ri-draft-line me-1"></i>Bozza</span>
                                                                ) : training.isAcknowledged ? (
                                                                    <span className="badge bg-success"><i className="ri-check-line me-1"></i>Confermato</span>
                                                                ) : (
                                                                    <span className="badge bg-warning text-dark">In attesa conferma</span>
                                                                )}
                                                            </div>
                                                        </div>

                                                        {expandedTraining === training.id && (
                                                            <div className="p-4 bg-light border-top">
                                                                <div className="bg-white rounded p-3 mb-3">
                                                                    <p style={{ whiteSpace: 'pre-line' }}>{training.content}</p>
                                                                </div>
                                                                {training.strengths && (
                                                                    <div className="rounded p-3 mb-3" style={{ background: '#d1fae5', borderLeft: '4px solid #10b981' }}>
                                                                        <h6 className="text-success mb-2"><i className="ri-thumb-up-line me-2"></i>Punti di Forza</h6>
                                                                        <p className="mb-0" style={{ whiteSpace: 'pre-line' }}>{training.strengths}</p>
                                                                    </div>
                                                                )}
                                                                {training.improvements && (
                                                                    <div className="rounded p-3 mb-3" style={{ background: '#fef3c7', borderLeft: '4px solid #f59e0b' }}>
                                                                        <h6 className="text-warning mb-2"><i className="ri-lightbulb-line me-2"></i>Aree di Miglioramento</h6>
                                                                        <p className="mb-0" style={{ whiteSpace: 'pre-line' }}>{training.improvements}</p>
                                                                    </div>
                                                                )}
                                                                {training.goals && (
                                                                    <div className="rounded p-3 mb-3" style={{ background: '#dbeafe', borderLeft: '4px solid #3b82f6' }}>
                                                                        <h6 className="text-primary mb-2"><i className="ri-focus-3-line me-2"></i>Obiettivi</h6>
                                                                        <p className="mb-0" style={{ whiteSpace: 'pre-line' }}>{training.goals}</p>
                                                                    </div>
                                                                )}

                                                                {training.isAcknowledged && (
                                                                    <div className="alert alert-success mb-3">
                                                                        <div className="d-flex align-items-center">
                                                                            <i className="ri-check-double-line fs-4 me-2"></i>
                                                                            <div>
                                                                                <strong>Confermato dal destinatario</strong>
                                                                                <span className="ms-2 text-muted small">il {formatDateTime(training.acknowledgedAt)}</span>
                                                                                {training.acknowledgmentNotes && <p className="mb-0 mt-1 small">{training.acknowledgmentNotes}</p>}
                                                                            </div>
                                                                        </div>
                                                                    </div>
                                                                )}

                                                                {/* Messages */}
                                                                <div className="bg-white rounded p-3">
                                                                    <h6 className="mb-3"><i className="ri-chat-3-line me-2"></i>Discussione</h6>
                                                                    <div className="mb-3" style={{ maxHeight: '200px', overflowY: 'auto' }}>
                                                                        {(!training.messages || training.messages.length === 0) ? (
                                                                            <p className="text-muted small text-center py-3">Nessun messaggio.</p>
                                                                        ) : (
                                                                            training.messages.map(msg => (
                                                                                <div key={msg.id} className={`p-2 rounded mb-2 ${msg.isOwn ? 'ms-5' : 'me-5'}`} style={{ background: msg.isOwn ? '#e3f2fd' : '#f5f5f5' }}>
                                                                                    <div className="d-flex justify-content-between mb-1">
                                                                                        <strong className="small">{msg.senderName}</strong>
                                                                                        <span className="text-muted small">{formatDate(msg.createdAt)}</span>
                                                                                    </div>
                                                                                    <p className="mb-0 small">{msg.content}</p>
                                                                                </div>
                                                                            ))
                                                                        )}
                                                                    </div>
                                                                    <div className="input-group">
                                                                        <input type="text" className="form-control" placeholder="Scrivi un messaggio..." value={newMessage}
                                                                            onChange={(e) => setNewMessage(e.target.value)}
                                                                            onKeyPress={(e) => { if (e.key === 'Enter' && !actionLoading) handleSendMessage(training.id); }}
                                                                            onClick={(e) => e.stopPropagation()} disabled={actionLoading} />
                                                                        <button className="btn btn-primary" onClick={(e) => { e.stopPropagation(); handleSendMessage(training.id); }} disabled={actionLoading || !newMessage.trim()}>
                                                                            {actionLoading ? <span className="spinner-border spinner-border-sm"></span> : <i className="ri-send-plane-line"></i>}
                                                                        </button>
                                                                    </div>
                                                                </div>
                                                            </div>
                                                        )}
                                                    </div>
                                                ))
                                            )}
                                            {/* Paginazione Training Erogati */}
                                            {filteredGivenTrainings.length > ITEMS_PER_SECTION && (() => {
                                                const tp = Math.ceil(filteredGivenTrainings.length / ITEMS_PER_SECTION);
                                                return (
                                                <div className="form-pagination">
                                                    <span className="form-pagination-info">
                                                        {Math.min((givenTrainingsPage - 1) * ITEMS_PER_SECTION + 1, filteredGivenTrainings.length)}-{Math.min(givenTrainingsPage * ITEMS_PER_SECTION, filteredGivenTrainings.length)} di {filteredGivenTrainings.length}
                                                    </span>
                                                    <div className="form-pagination-buttons">
                                                        <button className="form-page-btn" disabled={givenTrainingsPage === 1} onClick={() => setGivenTrainingsPage(p => Math.max(1, p - 1))}>&laquo;</button>
                                                        {Array.from({ length: tp }, (_, i) => i + 1)
                                                            .filter(p => p >= Math.max(1, givenTrainingsPage - 2) && p <= Math.min(tp, givenTrainingsPage + 2))
                                                            .map(p => (
                                                                <button key={p} className={`form-page-btn${givenTrainingsPage === p ? ' active' : ''}`} onClick={() => setGivenTrainingsPage(p)}>{p}</button>
                                                            ))}
                                                        <button className="form-page-btn" disabled={givenTrainingsPage >= tp} onClick={() => setGivenTrainingsPage(p => Math.min(tp, p + 1))}>&raquo;</button>
                                                    </div>
                                                </div>
                                                );
                                            })()}
                                        </div>
                                    )}

                                    {/* Received Requests List - Richieste Ricevute */}
                                    {activeTab === 'received' && (
                                        <div>
                                            {filteredReceivedRequests.length === 0 ? (
                                                <div className="text-center py-5">
                                                    <i className="ri-mail-download-line text-muted" style={{ fontSize: '64px' }}></i>
                                                    <h5 className="mt-3 mb-1">Nessuna richiesta ricevuta</h5>
                                                    <p className="text-muted">Non hai ricevuto richieste di training.</p>
                                                </div>
                                            ) : (
                                                filteredReceivedRequests.slice((receivedRequestsPage - 1) * ITEMS_PER_SECTION, receivedRequestsPage * ITEMS_PER_SECTION).map(request => (
                                                    <div key={request.id} className="border-bottom">
                                                        <div
                                                            className="p-3 d-flex justify-content-between align-items-start"
                                                            style={{ cursor: 'pointer', background: expandedRequest === request.id ? '#f8f9fa' : 'white' }}
                                                            onClick={() => setExpandedRequest(expandedRequest === request.id ? null : request.id)}
                                                        >
                                                            <div className="flex-grow-1">
                                                                <div className="d-flex align-items-center gap-2 mb-1">
                                                                    <h6 className="mb-0">{request.subject}</h6>
                                                                    <i className={`ri-arrow-${expandedRequest === request.id ? 'up' : 'down'}-s-line`}></i>
                                                                </div>
                                                                <div className="d-flex flex-wrap gap-2 align-items-center text-muted small">
                                                                    <span><i className="ri-user-line me-1"></i>Da: {request.requester?.firstName} {request.requester?.lastName}</span>
                                                                    <span><i className="ri-calendar-line me-1"></i>{formatDate(request.createdAt)}</span>
                                                                </div>
                                                            </div>
                                                            <div className="d-flex gap-2 flex-wrap justify-content-end">
                                                                <span className="badge" style={{ background: `${PRIORITIES[request.priority]?.color || '#6c757d'}20`, color: PRIORITIES[request.priority]?.color || '#6c757d' }}>
                                                                    {PRIORITIES[request.priority]?.label || request.priority}
                                                                </span>
                                                                {request.status === 'pending' && <span className="badge bg-info"><i className="ri-time-line me-1"></i>Da gestire</span>}
                                                                {request.status === 'accepted' && <span className="badge bg-primary"><i className="ri-check-line me-1"></i>Accettata</span>}
                                                                {request.status === 'completed' && <span className="badge bg-success"><i className="ri-check-double-line me-1"></i>Completata</span>}
                                                                {request.status === 'rejected' && <span className="badge bg-danger"><i className="ri-close-line me-1"></i>Rifiutata</span>}
                                                            </div>
                                                        </div>

                                                        {expandedRequest === request.id && (
                                                            <div className="p-4 bg-light border-top">
                                                                {request.description && (
                                                                    <div className="rounded p-3 mb-3" style={{ background: 'white', borderLeft: '4px solid #0dcaf0' }}>
                                                                        <h6 className="mb-2"><i className="ri-file-text-line me-2"></i>Descrizione Richiesta</h6>
                                                                        <p className="mb-0">{request.description}</p>
                                                                    </div>
                                                                )}

                                                                {request.status === 'pending' && (
                                                                    <>
                                                                        <div className="alert alert-info">
                                                                            <i className="ri-information-line me-2"></i>
                                                                            <strong>Questa richiesta è in attesa di risposta.</strong>
                                                                            <p className="mb-0 mt-2 small text-muted">
                                                                                Gestisci questa richiesta da questa sezione (Formazione): accettazione/risposta e creazione training sono qui.
                                                                            </p>
                                                                        </div>
                                                                        <div className="bg-white rounded border p-3 mb-3">
                                                                            <label className="form-label fw-semibold mb-2">
                                                                                <i className="ri-chat-3-line me-2"></i>
                                                                                Risposta / Note al collega
                                                                            </label>
                                                                            <textarea
                                                                                className="form-control"
                                                                                rows="3"
                                                                                placeholder="Scrivi una risposta rapida (es. ok, creo il training oggi / ci sentiamo in call / ecc.)"
                                                                                value={requestResponseDrafts[request.id] ?? (request.responseNotes || '')}
                                                                                onChange={(e) => setRequestResponseDrafts(prev => ({ ...prev, [request.id]: e.target.value }))}
                                                                                onClick={(e) => e.stopPropagation()}
                                                                                disabled={requestResponseLoadingId === request.id}
                                                                            />
                                                                            <div className="d-flex flex-wrap gap-2 mt-3">
                                                                                <button
                                                                                    className="btn btn-success btn-sm"
                                                                                    onClick={(e) => {
                                                                                        e.stopPropagation();
                                                                                        handleRespondToReceivedRequest(request, 'accept');
                                                                                    }}
                                                                                    disabled={requestResponseLoadingId === request.id}
                                                                                >
                                                                                    {requestResponseLoadingId === request.id ? (
                                                                                        <span className="spinner-border spinner-border-sm me-1"></span>
                                                                                    ) : (
                                                                                        <i className="ri-check-line me-1"></i>
                                                                                    )}
                                                                                    Accetta
                                                                                </button>
                                                                                <button
                                                                                    className="btn btn-outline-danger btn-sm"
                                                                                    onClick={(e) => {
                                                                                        e.stopPropagation();
                                                                                        handleRespondToReceivedRequest(request, 'reject');
                                                                                    }}
                                                                                    disabled={requestResponseLoadingId === request.id}
                                                                                >
                                                                                    <i className="ri-close-line me-1"></i>
                                                                                    Rifiuta
                                                                                </button>
                                                                            </div>
                                                                        </div>
                                                                    </>
                                                                )}

                                                                {request.status === 'completed' && request.reviewId && (
                                                                    <div className="alert alert-success">
                                                                        <i className="ri-check-double-line me-2"></i>
                                                                        <strong>Training completato!</strong>
                                                                    </div>
                                                                )}

                                                                {request.status === 'accepted' && (
                                                                    <div className="alert alert-primary d-flex justify-content-between align-items-center flex-wrap gap-2">
                                                                        <div>
                                                                            <i className="ri-check-line me-2"></i>
                                                                            <strong>Richiesta accettata</strong>
                                                                            {request.respondedAt && (
                                                                                <span className="small ms-2">il {formatDateTime(request.respondedAt)}</span>
                                                                            )}
                                                                            {request.responseNotes && (
                                                                                <div className="small mt-2">
                                                                                    <strong>Risposta:</strong> {request.responseNotes}
                                                                                </div>
                                                                            )}
                                                                        </div>
                                                                        <button
                                                                            className="btn btn-primary btn-sm"
                                                                            onClick={(e) => {
                                                                                e.stopPropagation();
                                                                                handleOpenTrainingFromRequest(request);
                                                                            }}
                                                                            disabled={actionLoading}
                                                                        >
                                                                            <i className="ri-edit-line me-1"></i>
                                                                            Scrivi Training
                                                                        </button>
                                                                    </div>
                                                                )}

                                                                {request.status === 'rejected' && request.responseNotes && (
                                                                    <div className="alert alert-danger mb-0">
                                                                        <i className="ri-chat-3-line me-2"></i>
                                                                        <strong>Risposta inviata</strong>
                                                                        <div className="small mt-2">{request.responseNotes}</div>
                                                                    </div>
                                                                )}
                                                            </div>
                                                        )}
                                                    </div>
                                                ))
                                            )}
                                            {/* Paginazione Richieste Ricevute */}
                                            {filteredReceivedRequests.length > ITEMS_PER_SECTION && (() => {
                                                const tp = Math.ceil(filteredReceivedRequests.length / ITEMS_PER_SECTION);
                                                return (
                                                <div className="form-pagination">
                                                    <span className="form-pagination-info">
                                                        {Math.min((receivedRequestsPage - 1) * ITEMS_PER_SECTION + 1, filteredReceivedRequests.length)}-{Math.min(receivedRequestsPage * ITEMS_PER_SECTION, filteredReceivedRequests.length)} di {filteredReceivedRequests.length}
                                                    </span>
                                                    <div className="form-pagination-buttons">
                                                        <button className="form-page-btn" disabled={receivedRequestsPage === 1} onClick={() => setReceivedRequestsPage(p => Math.max(1, p - 1))}>&laquo;</button>
                                                        {Array.from({ length: tp }, (_, i) => i + 1)
                                                            .filter(p => p >= Math.max(1, receivedRequestsPage - 2) && p <= Math.min(tp, receivedRequestsPage + 2))
                                                            .map(p => (
                                                                <button key={p} className={`form-page-btn${receivedRequestsPage === p ? ' active' : ''}`} onClick={() => setReceivedRequestsPage(p)}>{p}</button>
                                                            ))}
                                                        <button className="form-page-btn" disabled={receivedRequestsPage >= tp} onClick={() => setReceivedRequestsPage(p => Math.min(tp, p + 1))}>&raquo;</button>
                                                    </div>
                                                </div>
                                                );
                                            })()}
                                        </div>
                                    )}

                                </div>
                            </div>
                        </>
                    )}

                    {/* Tab Content: Gestione Team */}
                    {adminTab === 'team' && (
                        <>
                            {/* Filters */}
                            <div className="card shadow-sm border-0 mb-4">
                                <div className="card-body py-3">
                                    <div className="row g-2 align-items-center">
                                        <div className="col-lg-6">
                                            <div className="position-relative">
                                                <i className="ri-search-line position-absolute text-muted" style={{ left: '12px', top: '50%', transform: 'translateY(-50%)' }}></i>
                                                <input
                                                    type="text"
                                                    className="form-control bg-light border-0"
                                                    placeholder="Cerca per nome o email..."
                                                    value={adminFilters.search}
                                                    onChange={(e) => handleAdminFilterChange('search', e.target.value)}
                                                    style={{ paddingLeft: '36px' }}
                                                />
                                            </div>
                                        </div>
                                        <div className="col-lg-4">
                                            <select
                                                className="form-select bg-light border-0"
                                                value={adminFilters.specialty}
                                                onChange={(e) => handleAdminFilterChange('specialty', e.target.value)}
                                                disabled={isTeamLeader && !!teamLeaderSpecialtyFilterValue}
                                            >
                                                <option value="">
                                                    {isTeamLeader && teamLeaderSpecialtyGroup
                                                        ? 'Solo la tua specialità'
                                                        : 'Tutte le Specializzazioni'}
                                                </option>
                                                {allowedSpecialtyFilterOptions.map((opt) => (
                                                    <option key={opt.value} value={opt.value}>{opt.label}</option>
                                                ))}
                                            </select>
                                        </div>
                                        <div className="col-lg-2">
                                            <button className="btn btn-outline-secondary w-100" onClick={resetAdminFilters}>
                                                <i className="ri-refresh-line me-1"></i>Reset
                                            </button>
                                        </div>
                                    </div>
                                </div>
                            </div>

                            {/* Card Grid */}
                            {filteredProfessionals.length === 0 ? (
                                <div className="card shadow-sm border-0">
                                    <div className="card-body text-center py-5">
                                        <i className="ri-user-search-line text-muted" style={{ fontSize: '5rem' }}></i>
                                        <h5 className="mt-3">Nessun professionista trovato</h5>
                                        <p className="text-muted mb-4">Prova a modificare i filtri di ricerca</p>
                                        <button className="btn btn-primary" onClick={resetAdminFilters}>
                                            <i className="ri-refresh-line me-2"></i>Reset Filtri
                                        </button>
                                    </div>
                                </div>
                            ) : (
                                <>
                                    <div className="row g-4">
                                        {paginatedProfessionals.map((member) => (
                                            <div key={member.id} className="col-xxl-3 col-xl-4 col-lg-4 col-md-6">
                                                <div className="card border-0 shadow-sm overflow-hidden" style={{ borderRadius: '12px' }}>
                                                    <div
                                                        className="position-relative"
                                                        style={{ background: SPECIALTY_GRADIENTS[member.specialty] || DEFAULT_GRADIENT, height: '70px' }}
                                                    >
                                                        <div className="position-absolute top-0 start-0 m-2">
                                                            <span className="badge small" style={{
                                                                background: '#fff',
                                                                color: ({
                                                                    nutrizione: '#16a34a', nutrizionista: '#16a34a',
                                                                    coach: '#ea580c',
                                                                    psicologia: '#db2777', psicologo: '#db2777',
                                                                })[member.specialty] || '#64748b',
                                                                fontWeight: 600,
                                                            }}>
                                                                {ROLE_LABELS[member.role] || 'N/D'}
                                                            </span>
                                                        </div>
                                                        <div className="position-absolute start-50 translate-middle" style={{ top: '100%' }}>
                                                            {member.avatarPath ? (
                                                                <img src={member.avatarPath} alt="" className="rounded-circle border border-3 border-white shadow-sm" style={{ width: '64px', height: '64px', objectFit: 'cover', background: '#fff' }} />
                                                            ) : (
                                                                <div className="rounded-circle border border-3 border-white shadow-sm d-flex align-items-center justify-content-center" style={{ width: '64px', height: '64px', background: '#fff' }}>
                                                                    <span className="fw-bold fs-5 text-primary">{member.firstName?.[0]?.toUpperCase()}{member.lastName?.[0]?.toUpperCase()}</span>
                                                                </div>
                                                            )}
                                                        </div>
                                                    </div>
                                                    <div className="card-body text-center pt-5 pb-3">
                                                        <h5 className="fw-semibold mb-1">{member.firstName} {member.lastName}</h5>
                                                        <p className="text-muted small mb-3" style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{member.email}</p>
                                                        {member.specialty && (() => {
                                                            const specColor = ({
                                                                nutrizione: '#16a34a', nutrizionista: '#16a34a',
                                                                coach: '#ea580c',
                                                                psicologia: '#db2777', psicologo: '#db2777',
                                                                health_manager: '#ec4899',
                                                            })[member.specialty] || '#64748b';
                                                            return (
                                                                <span className="badge rounded-pill px-2 py-1" style={{ fontSize: '11px', background: '#fff', color: specColor, border: `1px solid ${specColor}30` }}>
                                                                    {SPECIALTY_LABELS[member.specialty] || member.specialty}
                                                                </span>
                                                            );
                                                        })()}
                                                    </div>
                                                    <div className="card-footer border-0 py-2" style={{ background: 'transparent' }}>
                                                        <button
                                                            className="btn btn-sm w-100"
                                                            style={{
                                                                background: '#25B36A',
                                                                color: '#fff',
                                                                borderRadius: 20,
                                                                fontWeight: 600,
                                                                fontSize: 13,
                                                                border: 'none',
                                                                transition: 'all 0.2s ease',
                                                            }}
                                                            onMouseEnter={e => { e.currentTarget.style.background = '#1e9a5a'; e.currentTarget.style.boxShadow = '0 4px 12px rgba(37,179,106,0.3)'; }}
                                                            onMouseLeave={e => { e.currentTarget.style.background = '#25B36A'; e.currentTarget.style.boxShadow = 'none'; }}
                                                            onClick={() => handleSelectProfessional(member)}
                                                        >
                                                            <i className="ri-book-open-line me-1"></i>Vedi Training
                                                        </button>
                                                    </div>
                                                </div>
                                            </div>
                                        ))}
                                    </div>

                                    {/* Paginazione */}
                                    {totalPages > 1 && (
                                        <div className="form-pagination" style={{ marginTop: '20px' }}>
                                            <span className="form-pagination-info">
                                                Pagina {currentPage} di {totalPages} &middot; {filteredProfessionals.length} professionisti
                                            </span>
                                            <div className="form-pagination-buttons">
                                                <button className="form-page-btn" disabled={currentPage === 1} onClick={() => setCurrentPage(p => Math.max(1, p - 1))}>&laquo;</button>
                                                {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
                                                    let pageNum;
                                                    if (totalPages <= 5) pageNum = i + 1;
                                                    else if (currentPage <= 3) pageNum = i + 1;
                                                    else if (currentPage >= totalPages - 2) pageNum = totalPages - 4 + i;
                                                    else pageNum = currentPage - 2 + i;
                                                    return (
                                                        <button key={pageNum} className={`form-page-btn${currentPage === pageNum ? ' active' : ''}`} onClick={() => setCurrentPage(pageNum)}>{pageNum}</button>
                                                    );
                                                })}
                                                <button className="form-page-btn" disabled={currentPage === totalPages} onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))}>&raquo;</button>
                                            </div>
                                        </div>
                                    )}
                                </>
                            )}
                        </>
                    )}

                    </div>

                    {/* Acknowledge Modal */}
                    {showAckModal && (
                        <div className="modal fade show d-block" style={{ background: 'rgba(0,0,0,0.5)' }}>
                            <div className="modal-dialog modal-dialog-centered">
                                <div className="modal-content">
                                    <div className="modal-header">
                                        <h5 className="modal-title"><i className="ri-check-double-line me-2 text-success"></i>Conferma Lettura</h5>
                                        <button type="button" className="btn-close" onClick={() => { setShowAckModal(null); setAckNotes(''); }} disabled={actionLoading}></button>
                                    </div>
                                    <div className="modal-body">
                                        <p>Confermi di aver letto e compreso questo training?</p>
                                        <div className="mb-3">
                                            <label className="form-label">Note (opzionale)</label>
                                            <textarea className="form-control" rows="3" placeholder="Aggiungi un commento o una domanda..." value={ackNotes} onChange={(e) => setAckNotes(e.target.value)} disabled={actionLoading}></textarea>
                                        </div>
                                    </div>
                                    <div className="modal-footer">
                                        <button className="btn btn-light" onClick={() => { setShowAckModal(null); setAckNotes(''); }} disabled={actionLoading}>Annulla</button>
                                        <button className="btn btn-success" onClick={() => handleAcknowledge(showAckModal)} disabled={actionLoading}>
                                            {actionLoading ? <><span className="spinner-border spinner-border-sm me-2"></span>Confermando...</> : <><i className="ri-check-line me-2"></i>Conferma</>}
                                        </button>
                                    </div>
                                </div>
                            </div>
                        </div>
                    )}

                    <SupportWidget
                        pageTitle="Formazione e Sviluppo"
                        pageDescription="Gestisci la tua crescita professionale, visualizza i training assegnati e richiedi supporto formativo."
                        pageIcon={FaGraduationCap}
                        docsSection="formazione"
                        onStartTour={() => setMostraTour(true)}
                        brandName="Suite Clinica"
                        logoSrc="/suitemind.png"
                        accentColor="#6366F1"
                    />

                    <GuidedTour
                        steps={tourSteps}
                        isOpen={mostraTour}
                        onClose={() => setMostraTour(false)}
                        onComplete={() => {
                            setMostraTour(false);
                            console.log('Tour Formazione completato');
                        }}
                    />
                </div>
            );
        }

        // Vista training di un professionista
        if (adminView === 'trainings' && selectedProfessional) {
            const specialtyGradient = SPECIALTY_GRADIENTS[selectedProfessional.specialty] || DEFAULT_GRADIENT;

            return (
                <>
                    {/* Header semplice */}
                    <div className="d-flex flex-wrap align-items-center justify-content-between gap-3 mb-4">
                        <div className="d-flex align-items-center gap-3">
                            <button
                                className="btn btn-outline-secondary"
                                onClick={handleBackToProfessionals}
                            >
                                <i className="ri-arrow-left-line"></i>
                            </button>

                            {/* Avatar */}
                            <div
                                className="rounded-circle d-flex align-items-center justify-content-center overflow-hidden"
                                style={{
                                    width: '56px',
                                    height: '56px',
                                    minWidth: '56px',
                                    background: specialtyGradient,
                                    fontSize: '20px',
                                    fontWeight: '600',
                                    color: '#fff'
                                }}
                            >
                                {selectedProfessional.avatarPath ? (
                                    <img
                                        src={selectedProfessional.avatarPath}
                                        alt=""
                                        style={{ width: '100%', height: '100%', objectFit: 'cover' }}
                                    />
                                ) : (
                                    `${selectedProfessional.firstName?.charAt(0) || ''}${selectedProfessional.lastName?.charAt(0) || ''}`
                                )}
                            </div>

                            {/* Info */}
                            <div>
                                <h4 className="mb-0 fw-bold">
                                    {selectedProfessional.firstName} {selectedProfessional.lastName}
                                </h4>
                                <p className="text-muted mb-0 small">
                                    {selectedProfessional.jobTitle || 'Professionista'} • {selectedProfessional.department || '-'}
                                </p>
                            </div>
                        </div>

                        <button
                            className="btn btn-success"
                            onClick={() => setShowNewTrainingModal(true)}
                        >
                            <i className="ri-edit-line me-2"></i>
                            Scrivi Training
                        </button>
                    </div>

                    {/* Stats */}
                    <div className="row g-3 mb-4">
                        <div className="col-xl-4 col-sm-6">
                            <div className="card border-0 shadow-sm">
                                <div className="card-body">
                                    <div className="d-flex align-items-center">
                                        <div className="rounded-circle d-flex align-items-center justify-content-center"
                                            style={{ width: '48px', height: '48px', background: 'rgba(111, 66, 193, 0.1)' }}>
                                            <i className="ri-book-open-line fs-4" style={{ color: '#6f42c1' }}></i>
                                        </div>
                                        <div className="ms-3">
                                            <h3 className="mb-0 fw-bold">{professionalTrainings.length}</h3>
                                            <span className="text-muted small">Training Totali</span>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                        <div className="col-xl-4 col-sm-6">
                            <div className="card border-0 shadow-sm">
                                <div className="card-body">
                                    <div className="d-flex align-items-center">
                                        <div className="rounded-circle d-flex align-items-center justify-content-center"
                                            style={{ width: '48px', height: '48px', background: 'rgba(255, 193, 7, 0.2)' }}>
                                            <i className="ri-time-line fs-4 text-warning"></i>
                                        </div>
                                        <div className="ms-3">
                                            <h3 className="mb-0 fw-bold">
                                                {professionalTrainings.filter(t => !t.isAcknowledged && !t.isDraft).length}
                                            </h3>
                                            <span className="text-muted small">Da Confermare</span>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                        <div className="col-xl-4 col-sm-6">
                            <div className="card border-0 shadow-sm">
                                <div className="card-body">
                                    <div className="d-flex align-items-center">
                                        <div className="rounded-circle d-flex align-items-center justify-content-center"
                                            style={{ width: '48px', height: '48px', background: 'rgba(25, 135, 84, 0.1)' }}>
                                            <i className="ri-check-double-line fs-4 text-success"></i>
                                        </div>
                                        <div className="ms-3">
                                            <h3 className="mb-0 fw-bold">
                                                {professionalTrainings.filter(t => t.isAcknowledged).length}
                                            </h3>
                                            <span className="text-muted small">Confermati</span>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>

                    {/* Training List */}
                    <div className="card">
                        <div className="card-header bg-white">
                            <h5 className="card-title mb-0">
                                <i className="ri-book-open-line me-2"></i>
                                Lista Training
                            </h5>
                        </div>
                        <div className="card-body p-0">
                            {professionalTrainings.length === 0 ? (
                                <div className="text-center py-5">
                                    <div className="rounded-circle d-inline-flex align-items-center justify-content-center mb-3"
                                        style={{ width: '100px', height: '100px', background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)' }}>
                                        <i className="ri-book-open-line text-white" style={{ fontSize: '48px' }}></i>
                                    </div>
                                    <h5 className="mt-3 mb-2">Nessun training ancora</h5>
                                    <p className="text-muted mb-4">
                                        {selectedProfessional.firstName} non ha ancora ricevuto training.<br />
                                        Scrivi il primo training per iniziare!
                                    </p>
                                    <button
                                        className="btn btn-success btn-lg"
                                        onClick={() => setShowNewTrainingModal(true)}
                                    >
                                        <i className="ri-edit-line me-2"></i>
                                        Scrivi il Primo Training
                                    </button>
                                </div>
                            ) : (
                                professionalTrainings.map(training => (
                                    <div key={training.id} className="border-bottom">
                                        {/* Training Header */}
                                        <div
                                            className="p-3 d-flex justify-content-between align-items-start"
                                            style={{
                                                cursor: 'pointer',
                                                background: expandedTraining === training.id ? '#f8f9fa' : 'white',
                                            }}
                                            onClick={() => setExpandedTraining(expandedTraining === training.id ? null : training.id)}
                                        >
                                            <div className="flex-grow-1">
                                                <div className="d-flex align-items-center gap-2 mb-1">
                                                    <h6 className="mb-0">{training.title}</h6>
                                                    <i className={`ri-arrow-${expandedTraining === training.id ? 'up' : 'down'}-s-line`}></i>
                                                </div>
                                                <div className="d-flex flex-wrap gap-2 align-items-center text-muted small">
                                                    <span>
                                                        <i className="ri-user-line me-1"></i>
                                                        Da: {training.reviewer?.firstName} {training.reviewer?.lastName}
                                                    </span>
                                                    <span>
                                                        <i className="ri-calendar-line me-1"></i>
                                                        {formatDate(training.createdAt)}
                                                    </span>
                                                </div>
                                            </div>
                                            <div className="d-flex gap-2 flex-wrap justify-content-end">
                                                <span
                                                    className="badge"
                                                    style={{
                                                        background: `${TRAINING_TYPES[training.reviewType]?.color || '#6c757d'}20`,
                                                        color: TRAINING_TYPES[training.reviewType]?.color || '#6c757d'
                                                    }}
                                                >
                                                    {TRAINING_TYPES[training.reviewType]?.label || training.reviewType}
                                                </span>
                                                {training.isDraft && (
                                                    <span className="badge bg-secondary">Bozza</span>
                                                )}
                                                {training.isAcknowledged ? (
                                                    <span className="badge bg-success">
                                                        <i className="ri-check-line me-1"></i>Confermato
                                                    </span>
                                                ) : !training.isDraft && (
                                                    <span className="badge bg-warning text-dark">
                                                        Da confermare
                                                    </span>
                                                )}
                                            </div>
                                        </div>

                                        {/* Training Content (Expanded) */}
                                        {expandedTraining === training.id && (
                                            <div className="p-4 bg-light border-top">
                                                {/* Period */}
                                                {(training.periodStart || training.periodEnd) && (
                                                    <p className="text-muted small mb-3">
                                                        <i className="ri-calendar-2-line me-1"></i>
                                                        Periodo: {training.periodStart || '-'} - {training.periodEnd || '-'}
                                                    </p>
                                                )}

                                                {/* Main Content */}
                                                <div className="bg-white rounded p-3 mb-3">
                                                    <p style={{ whiteSpace: 'pre-line' }}>{training.content}</p>
                                                </div>

                                                {/* Strengths */}
                                                {training.strengths && (
                                                    <div className="rounded p-3 mb-3" style={{ background: '#d1fae5', borderLeft: '4px solid #10b981' }}>
                                                        <h6 className="text-success mb-2">
                                                            <i className="ri-thumb-up-line me-2"></i>Punti di Forza
                                                        </h6>
                                                        <p className="mb-0" style={{ whiteSpace: 'pre-line' }}>{training.strengths}</p>
                                                    </div>
                                                )}

                                                {/* Improvements */}
                                                {training.improvements && (
                                                    <div className="rounded p-3 mb-3" style={{ background: '#fef3c7', borderLeft: '4px solid #f59e0b' }}>
                                                        <h6 className="text-warning mb-2">
                                                            <i className="ri-lightbulb-line me-2"></i>Aree di Miglioramento
                                                        </h6>
                                                        <p className="mb-0" style={{ whiteSpace: 'pre-line' }}>{training.improvements}</p>
                                                    </div>
                                                )}

                                                {/* Goals */}
                                                {training.goals && (
                                                    <div className="rounded p-3 mb-3" style={{ background: '#dbeafe', borderLeft: '4px solid #3b82f6' }}>
                                                        <h6 className="text-primary mb-2">
                                                            <i className="ri-focus-3-line me-2"></i>Obiettivi
                                                        </h6>
                                                        <p className="mb-0" style={{ whiteSpace: 'pre-line' }}>{training.goals}</p>
                                                    </div>
                                                )}

                                                {/* Acknowledgment Status */}
                                                {training.isAcknowledged ? (
                                                    <div className="alert alert-success mb-3">
                                                        <div className="d-flex align-items-center">
                                                            <i className="ri-check-double-line fs-4 me-2"></i>
                                                            <div>
                                                                <strong>Confermato</strong>
                                                                <span className="ms-2 text-muted small">
                                                                    il {formatDateTime(training.acknowledgedAt)}
                                                                </span>
                                                                {training.acknowledgmentNotes && (
                                                                    <p className="mb-0 mt-1 small">{training.acknowledgmentNotes}</p>
                                                                )}
                                                            </div>
                                                        </div>
                                                    </div>
                                                ) : !training.isDraft && (
                                                    <div className="alert alert-warning mb-3">
                                                        <i className="ri-time-line me-2"></i>
                                                        <strong>In attesa di conferma</strong>
                                                    </div>
                                                )}

                                                {/* Messages (read-only for admin) */}
                                                {training.messages && training.messages.length > 0 && (
                                                    <div className="bg-white rounded p-3">
                                                        <h6 className="mb-3">
                                                            <i className="ri-chat-3-line me-2"></i>
                                                            Discussione ({training.messages.length} messaggi)
                                                        </h6>
                                                        <div style={{ maxHeight: '200px', overflowY: 'auto' }}>
                                                            {training.messages.map(msg => (
                                                                <div
                                                                    key={msg.id}
                                                                    className="p-2 rounded mb-2"
                                                                    style={{ background: '#f5f5f5' }}
                                                                >
                                                                    <div className="d-flex justify-content-between mb-1">
                                                                        <strong className="small">{msg.senderName}</strong>
                                                                        <span className="text-muted small">{formatDate(msg.createdAt)}</span>
                                                                    </div>
                                                                    <p className="mb-0 small">{msg.content}</p>
                                                                </div>
                                                            ))}
                                                        </div>
                                                    </div>
                                                )}
                                            </div>
                                        )}
                                    </div>
                                ))
                            )}
                        </div>
                    </div>

                    {/* Modal Nuovo Training */}
                    {showNewTrainingModal && (
                        <div className="modal fade show d-block" style={{ background: 'rgba(0,0,0,0.5)' }}>
                            <div className="modal-dialog modal-lg modal-dialog-centered modal-dialog-scrollable">
                                <div className="modal-content">
                                    <div className="modal-header" style={{ background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)' }}>
                                        <h5 className="modal-title text-white">
                                            <i className="ri-edit-line me-2"></i>
                                            Nuovo Training per {selectedProfessional.firstName} {selectedProfessional.lastName}
                                        </h5>
                                        <button
                                            type="button"
                                            className="btn-close btn-close-white"
                                            onClick={() => setShowNewTrainingModal(false)}
                                            disabled={actionLoading}
                                        ></button>
                                    </div>
                                    <div className="modal-body">
                                        {/* Titolo */}
                                        <div className="mb-3">
                                            <label className="form-label fw-semibold">Titolo *</label>
                                            <input
                                                type="text"
                                                className="form-control"
                                                placeholder="Es: Feedback trimestrale Q1 2025"
                                                value={newTraining.title}
                                                onChange={(e) => setNewTraining(prev => ({ ...prev, title: e.target.value }))}
                                                disabled={actionLoading}
                                            />
                                        </div>

                                        {/* Tipo e Periodo */}
                                        <div className="row g-3 mb-3">
                                            <div className="col-md-4">
                                                <label className="form-label fw-semibold">Tipo</label>
                                                <select
                                                    className="form-select"
                                                    value={newTraining.review_type}
                                                    onChange={(e) => setNewTraining(prev => ({ ...prev, review_type: e.target.value }))}
                                                    disabled={actionLoading}
                                                >
                                                    <option value="general">Generale</option>
                                                    <option value="performance">Performance</option>
                                                    <option value="progetto">Progetto</option>
                                                    <option value="monthly">Mensile</option>
                                                    <option value="annual">Annuale</option>
                                                </select>
                                            </div>
                                            <div className="col-md-4">
                                                <label className="form-label fw-semibold">Periodo Inizio</label>
                                                <input
                                                    type="date"
                                                    className="form-control"
                                                    value={newTraining.period_start}
                                                    onChange={(e) => setNewTraining(prev => ({ ...prev, period_start: e.target.value }))}
                                                    disabled={actionLoading}
                                                />
                                            </div>
                                            <div className="col-md-4">
                                                <label className="form-label fw-semibold">Periodo Fine</label>
                                                <input
                                                    type="date"
                                                    className="form-control"
                                                    value={newTraining.period_end}
                                                    onChange={(e) => setNewTraining(prev => ({ ...prev, period_end: e.target.value }))}
                                                    disabled={actionLoading}
                                                />
                                            </div>
                                        </div>

                                        {/* Contenuto */}
                                        <div className="mb-3">
                                            <label className="form-label fw-semibold">Contenuto del Training *</label>
                                            <textarea
                                                className="form-control"
                                                rows="5"
                                                placeholder="Descrivi il feedback generale, le attività svolte, i risultati raggiunti..."
                                                value={newTraining.content}
                                                onChange={(e) => setNewTraining(prev => ({ ...prev, content: e.target.value }))}
                                                disabled={actionLoading}
                                            ></textarea>
                                        </div>

                                        {/* Punti di Forza */}
                                        <div className="mb-3">
                                            <label className="form-label fw-semibold text-success">
                                                <i className="ri-thumb-up-line me-1"></i>
                                                Punti di Forza
                                            </label>
                                            <textarea
                                                className="form-control"
                                                rows="3"
                                                placeholder="Quali sono i punti di forza dimostrati? Cosa ha fatto particolarmente bene?"
                                                value={newTraining.strengths}
                                                onChange={(e) => setNewTraining(prev => ({ ...prev, strengths: e.target.value }))}
                                                disabled={actionLoading}
                                                style={{ borderColor: '#22c55e20' }}
                                            ></textarea>
                                        </div>

                                        {/* Aree di Miglioramento */}
                                        <div className="mb-3">
                                            <label className="form-label fw-semibold text-warning">
                                                <i className="ri-lightbulb-line me-1"></i>
                                                Aree di Miglioramento
                                            </label>
                                            <textarea
                                                className="form-control"
                                                rows="3"
                                                placeholder="Su cosa dovrebbe lavorare? Quali aspetti possono essere migliorati?"
                                                value={newTraining.improvements}
                                                onChange={(e) => setNewTraining(prev => ({ ...prev, improvements: e.target.value }))}
                                                disabled={actionLoading}
                                                style={{ borderColor: '#f59e0b20' }}
                                            ></textarea>
                                        </div>

                                        {/* Obiettivi */}
                                        <div className="mb-3">
                                            <label className="form-label fw-semibold text-primary">
                                                <i className="ri-focus-3-line me-1"></i>
                                                Obiettivi
                                            </label>
                                            <textarea
                                                className="form-control"
                                                rows="3"
                                                placeholder="Quali sono gli obiettivi per il prossimo periodo?"
                                                value={newTraining.goals}
                                                onChange={(e) => setNewTraining(prev => ({ ...prev, goals: e.target.value }))}
                                                disabled={actionLoading}
                                                style={{ borderColor: '#3b82f620' }}
                                            ></textarea>
                                        </div>
                                    </div>
                                    <div className="modal-footer">
                                        <button
                                            className="btn btn-light"
                                            onClick={() => setShowNewTrainingModal(false)}
                                            disabled={actionLoading}
                                        >
                                            Annulla
                                        </button>
                                        <button
                                            className="btn btn-success"
                                            onClick={handleCreateTraining}
                                            disabled={!newTraining.title.trim() || !newTraining.content.trim() || actionLoading}
                                        >
                                            {actionLoading ? (
                                                <>
                                                    <span className="spinner-border spinner-border-sm me-2"></span>
                                                    Salvataggio...
                                                </>
                                            ) : (
                                                <>
                                                    <i className="ri-save-line me-2"></i>
                                                    Salva Training
                                                </>
                                            )}
                                        </button>
                                    </div>
                                </div>
                            </div>
                        </div>
                    )}
                </>
            );
        }
    }

    // ==================== USER VIEW ====================
    return (
        <>
            {/* Page Header */}
            <div className="d-flex flex-wrap align-items-center justify-content-between gap-3 mb-4 position-relative" style={{ zIndex: 2 }}>
                <div>
                    <h4 className="mb-1">La tua Formazione</h4>
                    <p className="text-muted mb-0">
                        {stats.unacknowledged > 0
                            ? `${stats.unacknowledged} training da confermare`
                            : 'Tutti i training confermati'}
                    </p>
                </div>
                <button
                    className="btn btn-success"
                    onClick={() => setShowRequestModal(true)}
                    disabled={recipientsLoading}
                    style={{ position: 'relative', zIndex: 3 }}
                >
                    {recipientsLoading ? (
                        <>
                            <span className="spinner-border spinner-border-sm me-2"></span>
                            Caricamento...
                        </>
                    ) : (
                        <>
                            <i className="ri-add-circle-line me-2"></i>
                            Richiedi Training
                        </>
                    )}
                </button>
            </div>

            {/* Stats Cards */}
            <div className="row g-3 mb-4 align-items-start">
                {[
                    { label: 'Training Ricevuti', value: stats.totalTrainings, icon: 'ri-book-open-line', color: '#3b82f6', badge: stats.unacknowledged > 0 ? `${stats.unacknowledged} da confermare` : null },
                    { label: 'Richieste Inviate', value: requests.length, icon: 'ri-file-list-3-line', color: '#0dcaf0', badge: stats.pendingRequests > 0 ? `${stats.pendingRequests} in attesa` : null },
                    { label: 'Messaggi non letti', value: stats.unreadMessages, icon: 'ri-message-3-line', color: stats.unreadMessages > 0 ? '#f97316' : '#22c55e' },
                    { label: 'Completati', value: stats.completedRequests, icon: 'ri-check-double-line', color: '#22c55e' },
                ].map((stat, idx) => (
                    <div key={idx} className="col-xl-3 col-sm-6">
                        <div className="welcome-kpi-card-sm">
                            <div className="d-flex justify-content-between align-items-center">
                                <div>
                                    <div className="kpi-label">{stat.label}</div>
                                    <div className="kpi-value">{stat.value}</div>
                                    {stat.badge && <div style={{ marginTop: 4 }}><span className="badge bg-warning text-dark" style={{ fontSize: 11 }}>{stat.badge}</span></div>}
                                </div>
                                <div className="kpi-icon" style={{ background: `${stat.color}15`, color: stat.color }}>
                                    <i className={`${stat.icon} fs-5`}></i>
                                </div>
                            </div>
                        </div>
                    </div>
                ))}
            </div>

            {/* Tab Navigation */}
            <div className="card mb-4">
                <div className="card-header bg-white border-bottom">
                    <div className="formazione-tabs formazione-subtabs">
                        <button className={`formazione-tab${activeTab === 'trainings' ? ' active' : ''}`} onClick={() => setActiveTab('trainings')}>
                            <i className="ri-book-open-line"></i>
                            Training Ricevuti
                            {stats.unacknowledged > 0 && <span className="formazione-tab-badge danger">{stats.unacknowledged}</span>}
                        </button>
                        <button className={`formazione-tab${activeTab === 'requests' ? ' active' : ''}`} onClick={() => setActiveTab('requests')}>
                            <i className="ri-file-list-3-line"></i>
                            Le Mie Richieste
                            {stats.pendingRequests > 0 && <span className="formazione-tab-badge warning">{stats.pendingRequests}</span>}
                        </button>
                    </div>
                </div>
                <div className="px-3 py-2 border-bottom bg-white">
                    <div className="position-relative">
                        <i className="ri-search-line position-absolute text-muted" style={{ left: '12px', top: '50%', transform: 'translateY(-50%)' }}></i>
                        <input
                            type="text"
                            className="form-control bg-light border-0"
                            placeholder="Cerca training/richieste..."
                            value={listSearch}
                            onChange={(e) => setListSearch(e.target.value)}
                            style={{ paddingLeft: '36px' }}
                        />
                    </div>
                </div>

                <div className="card-body p-0">
                    {/* Training List */}
                    {activeTab === 'trainings' && (
                        <div>
                            {filteredTrainings.length === 0 ? (
                                <div className="text-center py-5">
                                    <i className="ri-book-open-line text-muted" style={{ fontSize: '64px' }}></i>
                                    <h5 className="mt-3 mb-1">Nessun training</h5>
                                    <p className="text-muted">Non hai ancora ricevuto training.</p>
                                    {recipients.length > 0 && (
                                        <button className="btn btn-success" onClick={() => setShowRequestModal(true)}>
                                            <i className="ri-add-circle-line me-2"></i>
                                            Richiedi il tuo primo training
                                        </button>
                                    )}
                                </div>
                            ) : (
                                filteredTrainings.map(training => (
                                    <div key={training.id} className="border-bottom">
                                        {/* Training Header */}
                                        <div
                                            className="p-3 d-flex justify-content-between align-items-start"
                                            style={{
                                                cursor: 'pointer',
                                                background: expandedTraining === training.id ? '#f8f9fa' : 'white',
                                            }}
                                            onClick={() => setExpandedTraining(expandedTraining === training.id ? null : training.id)}
                                        >
                                            <div className="flex-grow-1">
                                                <div className="d-flex align-items-center gap-2 mb-1">
                                                    <h6 className="mb-0">{training.title}</h6>
                                                    <i className={`ri-arrow-${expandedTraining === training.id ? 'up' : 'down'}-s-line`}></i>
                                                </div>
                                                <div className="d-flex flex-wrap gap-2 align-items-center text-muted small">
                                                    <span><i className="ri-user-line me-1"></i>{training.reviewer?.firstName} {training.reviewer?.lastName}</span>
                                                    <span><i className="ri-calendar-line me-1"></i>{formatDate(training.createdAt)}</span>
                                                </div>
                                            </div>
                                            <div className="d-flex gap-2 flex-wrap justify-content-end">
                                                <span className="badge" style={{ background: `${TRAINING_TYPES[training.reviewType]?.color || '#6c757d'}20`, color: TRAINING_TYPES[training.reviewType]?.color || '#6c757d' }}>
                                                    {TRAINING_TYPES[training.reviewType]?.label || training.reviewType}
                                                </span>
                                                {training.isAcknowledged ? (
                                                    <span className="badge bg-success"><i className="ri-check-line me-1"></i>Confermato</span>
                                                ) : (
                                                    <span className="badge bg-warning text-dark">Da confermare</span>
                                                )}
                                                {training.unreadCount > 0 && (
                                                    <span className="badge bg-danger"><i className="ri-message-3-line me-1"></i>{training.unreadCount}</span>
                                                )}
                                            </div>
                                        </div>

                                        {/* Training Content (Expanded) */}
                                        {expandedTraining === training.id && (
                                            <div className="p-4 bg-light border-top">
                                                {(training.periodStart || training.periodEnd) && (
                                                    <p className="text-muted small mb-3">
                                                        <i className="ri-calendar-2-line me-1"></i>
                                                        Periodo: {training.periodStart || '-'} - {training.periodEnd || '-'}
                                                    </p>
                                                )}

                                                <div className="bg-white rounded p-3 mb-3">
                                                    <p style={{ whiteSpace: 'pre-line' }}>{training.content}</p>
                                                </div>

                                                {training.strengths && (
                                                    <div className="rounded p-3 mb-3" style={{ background: '#d1fae5', borderLeft: '4px solid #10b981' }}>
                                                        <h6 className="text-success mb-2"><i className="ri-thumb-up-line me-2"></i>Punti di Forza</h6>
                                                        <p className="mb-0" style={{ whiteSpace: 'pre-line' }}>{training.strengths}</p>
                                                    </div>
                                                )}

                                                {training.improvements && (
                                                    <div className="rounded p-3 mb-3" style={{ background: '#fef3c7', borderLeft: '4px solid #f59e0b' }}>
                                                        <h6 className="text-warning mb-2"><i className="ri-lightbulb-line me-2"></i>Aree di Miglioramento</h6>
                                                        <p className="mb-0" style={{ whiteSpace: 'pre-line' }}>{training.improvements}</p>
                                                    </div>
                                                )}

                                                {training.goals && (
                                                    <div className="rounded p-3 mb-3" style={{ background: '#dbeafe', borderLeft: '4px solid #3b82f6' }}>
                                                        <h6 className="text-primary mb-2"><i className="ri-focus-3-line me-2"></i>Obiettivi</h6>
                                                        <p className="mb-0" style={{ whiteSpace: 'pre-line' }}>{training.goals}</p>
                                                    </div>
                                                )}

                                                {training.isAcknowledged ? (
                                                    <div className="alert alert-success mb-3">
                                                        <div className="d-flex align-items-center">
                                                            <i className="ri-check-double-line fs-4 me-2"></i>
                                                            <div>
                                                                <strong>Confermato</strong>
                                                                <span className="ms-2 text-muted small">il {formatDateTime(training.acknowledgedAt)}</span>
                                                                {training.acknowledgmentNotes && <p className="mb-0 mt-1 small">{training.acknowledgmentNotes}</p>}
                                                            </div>
                                                        </div>
                                                    </div>
                                                ) : (
                                                    <div className="alert alert-warning mb-3">
                                                        <div className="d-flex align-items-center justify-content-between flex-wrap gap-2">
                                                            <div>
                                                                <i className="ri-information-line me-2"></i>
                                                                <strong>Conferma di aver letto questo training</strong>
                                                            </div>
                                                            <button className="btn btn-success btn-sm" onClick={(e) => { e.stopPropagation(); setShowAckModal(training.id); }} disabled={actionLoading}>
                                                                <i className="ri-check-line me-1"></i>Conferma Lettura
                                                            </button>
                                                        </div>
                                                    </div>
                                                )}

                                                <div className="bg-white rounded p-3">
                                                    <h6 className="mb-3"><i className="ri-chat-3-line me-2"></i>Discussione</h6>
                                                    <div className="mb-3" style={{ maxHeight: '300px', overflowY: 'auto', minHeight: (training.messages?.length || 0) > 0 ? '100px' : '0' }}>
                                                        {(!training.messages || training.messages.length === 0) ? (
                                                            <p className="text-muted small text-center py-3">Nessun messaggio. Inizia la discussione!</p>
                                                        ) : (
                                                            training.messages.map(msg => (
                                                                <div key={msg.id} className={`p-2 rounded mb-2 ${msg.isOwn ? 'ms-5' : 'me-5'}`} style={{ background: msg.isOwn ? '#e3f2fd' : '#f5f5f5' }}>
                                                                    <div className="d-flex justify-content-between mb-1">
                                                                        <strong className="small">{msg.senderName}</strong>
                                                                        <span className="text-muted small">{formatDate(msg.createdAt)}</span>
                                                                    </div>
                                                                    <p className="mb-0 small">{msg.content}</p>
                                                                </div>
                                                            ))
                                                        )}
                                                    </div>
                                                    <div className="input-group">
                                                        <input type="text" className="form-control" placeholder="Scrivi un messaggio..." value={newMessage}
                                                            onChange={(e) => setNewMessage(e.target.value)}
                                                            onKeyPress={(e) => { if (e.key === 'Enter' && !actionLoading) handleSendMessage(training.id); }}
                                                            onClick={(e) => e.stopPropagation()} disabled={actionLoading} />
                                                        <button className="btn btn-primary" onClick={(e) => { e.stopPropagation(); handleSendMessage(training.id); }} disabled={actionLoading || !newMessage.trim()}>
                                                            {actionLoading ? <span className="spinner-border spinner-border-sm"></span> : <i className="ri-send-plane-line"></i>}
                                                        </button>
                                                    </div>
                                                </div>
                                            </div>
                                        )}
                                    </div>
                                ))
                            )}
                        </div>
                    )}

                    {/* Requests List */}
                    {activeTab === 'requests' && (
                        <div>
                            {filteredRequests.length === 0 ? (
                                <div className="text-center py-5">
                                    <i className="ri-file-list-3-line text-muted" style={{ fontSize: '64px' }}></i>
                                    <h5 className="mt-3 mb-1">Nessuna richiesta</h5>
                                    <p className="text-muted">Non hai ancora inviato richieste di training.</p>
                                    {recipients.length > 0 && (
                                        <button className="btn btn-success" onClick={() => setShowRequestModal(true)}>
                                            <i className="ri-add-circle-line me-2"></i>Invia la tua prima richiesta
                                        </button>
                                    )}
                                </div>
                            ) : (
                                filteredRequests.map(request => (
                                    <div key={request.id} className="border-bottom">
                                        <div
                                            className="p-3 d-flex justify-content-between align-items-start"
                                            style={{ cursor: 'pointer', background: expandedRequest === request.id ? '#f8f9fa' : 'white' }}
                                            onClick={() => setExpandedRequest(expandedRequest === request.id ? null : request.id)}
                                        >
                                            <div className="flex-grow-1">
                                                <div className="d-flex align-items-center gap-2 mb-1">
                                                    <h6 className="mb-0">{request.subject}</h6>
                                                    <i className={`ri-arrow-${expandedRequest === request.id ? 'up' : 'down'}-s-line`}></i>
                                                </div>
                                                <div className="d-flex flex-wrap gap-2 align-items-center text-muted small">
                                                    <span><i className="ri-user-line me-1"></i>A: {request.requestedTo?.firstName} {request.requestedTo?.lastName}</span>
                                                    <span><i className="ri-calendar-line me-1"></i>{formatDate(request.createdAt)}</span>
                                                </div>
                                            </div>
                                            <div className="d-flex gap-2 flex-wrap justify-content-end">
                                                <span className="badge" style={{ background: `${PRIORITIES[request.priority]?.color || '#6c757d'}20`, color: PRIORITIES[request.priority]?.color || '#6c757d' }}>
                                                    {PRIORITIES[request.priority]?.label || request.priority}
                                                </span>
                                                {request.status === 'pending' && <span className="badge bg-warning text-dark"><i className="ri-time-line me-1"></i>In Attesa</span>}
                                                {request.status === 'accepted' && <span className="badge bg-info"><i className="ri-check-line me-1"></i>In Preparazione</span>}
                                                {request.status === 'completed' && <span className="badge bg-success"><i className="ri-check-double-line me-1"></i>Completata</span>}
                                                {request.status === 'rejected' && <span className="badge bg-danger"><i className="ri-close-line me-1"></i>Rifiutata</span>}
                                            </div>
                                        </div>

                                        {expandedRequest === request.id && (
                                            <div className="p-4 bg-light border-top">
                                                {request.description && (
                                                    <div className="rounded p-3 mb-3" style={{ background: 'white', borderLeft: '4px solid #6f42c1' }}>
                                                        <h6 className="mb-2"><i className="ri-file-text-line me-2"></i>Descrizione</h6>
                                                        <p className="mb-0">{request.description}</p>
                                                    </div>
                                                )}

                                                {request.status === 'pending' && (
                                                    <>
                                                        <div className="alert alert-warning">
                                                            <i className="ri-time-line me-2"></i><strong>In attesa di risposta</strong>
                                                            <p className="mb-0 mt-1 small">La tua richiesta è stata inviata e verrà esaminata al più presto.</p>
                                                        </div>
                                                        <button className="btn btn-outline-danger btn-sm" onClick={(e) => { e.stopPropagation(); handleCancelRequest(request.id); }} disabled={actionLoading}>
                                                            {actionLoading ? <span className="spinner-border spinner-border-sm me-1"></span> : <i className="ri-delete-bin-line me-1"></i>}
                                                            Cancella Richiesta
                                                        </button>
                                                    </>
                                                )}

                                                {request.status === 'accepted' && (
                                                    <div className="alert alert-info">
                                                        <i className="ri-check-line me-2"></i><strong>Richiesta accettata</strong>
                                                        <p className="mb-0 mt-1 small">Il training è in preparazione.{request.respondedAt && <span> Accettata il {formatDateTime(request.respondedAt)}</span>}</p>
                                                        {request.responseNotes && <div className="mt-2 p-2 rounded" style={{ background: 'rgba(255,255,255,0.5)' }}><strong className="small">Note:</strong><p className="mb-0 small">{request.responseNotes}</p></div>}
                                                    </div>
                                                )}

                                                {request.status === 'completed' && (
                                                    <div className="alert alert-success d-flex justify-content-between align-items-center flex-wrap gap-2">
                                                        <div><i className="ri-check-double-line me-2"></i><strong>Training Completato!</strong></div>
                                                        {request.reviewId && (
                                                            <button className="btn btn-success btn-sm" onClick={(e) => { e.stopPropagation(); setExpandedTraining(request.reviewId); setActiveTab('trainings'); }}>
                                                                <i className="ri-eye-line me-1"></i>Visualizza Training
                                                            </button>
                                                        )}
                                                    </div>
                                                )}

                                                {request.status === 'rejected' && (
                                                    <>
                                                        <div className="alert alert-danger">
                                                            <i className="ri-close-circle-line me-2"></i><strong>Richiesta Rifiutata</strong>
                                                            {request.respondedAt && <span className="ms-2 small">il {formatDateTime(request.respondedAt)}</span>}
                                                        </div>
                                                        {request.responseNotes && (
                                                            <div className="rounded p-3" style={{ background: '#fee2e2', borderLeft: '4px solid #dc3545' }}>
                                                                <h6 className="mb-2 text-danger"><i className="ri-feedback-line me-2"></i>Motivazione</h6>
                                                                <p className="mb-0">{request.responseNotes}</p>
                                                            </div>
                                                        )}
                                                    </>
                                                )}
                                            </div>
                                        )}
                                    </div>
                                ))
                            )}
                        </div>
                    )}
                </div>
            </div>

            {/* Request Training Modal */}
            {showRequestModal && (
                <div className="modal fade show d-block" style={{ background: 'rgba(0,0,0,0.5)' }}>
                    <div className="modal-dialog modal-dialog-centered">
                        <div className="modal-content">
                            <div className="modal-header">
                                <h5 className="modal-title"><i className="ri-add-circle-line me-2"></i>Richiedi Training</h5>
                                <button type="button" className="btn-close" onClick={() => setShowRequestModal(false)} disabled={actionLoading}></button>
                            </div>
                            <div className="modal-body">
                                <div className="mb-3">
                                    <label className="form-label">Destinatario *</label>
                                    <select className="form-select" value={newRequest.recipient_id} onChange={(e) => setNewRequest(prev => ({ ...prev, recipient_id: e.target.value }))} disabled={actionLoading || recipientsLoading}>
                                        <option value="">Seleziona un destinatario...</option>
                                        {recipients.map(r => <option key={r.id} value={r.id}>{r.name} {r.role ? `- ${r.role}` : ''} {r.department ? `(${r.department})` : ''}</option>)}
                                    </select>
                                    {recipientsLoading && (
                                        <small className="text-muted d-block mt-2">Caricamento destinatari...</small>
                                    )}
                                    {!recipientsLoading && recipientsLoaded && recipients.length === 0 && (
                                        <small className="text-danger d-block mt-2">
                                            Nessun destinatario disponibile. Verificare assegnazione Team Leader / configurazione team.
                                        </small>
                                    )}
                                </div>
                                <div className="mb-3">
                                    <label className="form-label">Argomento *</label>
                                    <input type="text" className="form-control" placeholder="Es: Gestione pazienti diabetici" value={newRequest.subject} onChange={(e) => setNewRequest(prev => ({ ...prev, subject: e.target.value }))} disabled={actionLoading} />
                                </div>
                                <div className="mb-3">
                                    <label className="form-label">Descrizione</label>
                                    <textarea className="form-control" rows="4" placeholder="Descrivi cosa vorresti approfondire..." value={newRequest.description} onChange={(e) => setNewRequest(prev => ({ ...prev, description: e.target.value }))} disabled={actionLoading}></textarea>
                                </div>
                                <div className="mb-3">
                                    <label className="form-label">Priorità</label>
                                    <select className="form-select" value={newRequest.priority} onChange={(e) => setNewRequest(prev => ({ ...prev, priority: e.target.value }))} disabled={actionLoading}>
                                        <option value="low">Bassa</option>
                                        <option value="normal">Normale</option>
                                        <option value="high">Alta</option>
                                        <option value="urgent">Urgente</option>
                                    </select>
                                </div>
                            </div>
                            <div className="modal-footer">
                                <button className="btn btn-light" onClick={() => setShowRequestModal(false)} disabled={actionLoading}>Annulla</button>
                                <button className="btn btn-success" onClick={handleCreateRequest} disabled={!newRequest.subject.trim() || !newRequest.recipient_id || actionLoading}>
                                    {actionLoading ? <><span className="spinner-border spinner-border-sm me-2"></span>Invio...</> : <><i className="ri-send-plane-line me-2"></i>Invia Richiesta</>}
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            )}

            {/* Acknowledge Modal */}
            {showAckModal && (
                <div className="modal fade show d-block" style={{ background: 'rgba(0,0,0,0.5)' }}>
                    <div className="modal-dialog modal-dialog-centered">
                        <div className="modal-content">
                            <div className="modal-header">
                                <h5 className="modal-title"><i className="ri-check-double-line me-2 text-success"></i>Conferma Lettura</h5>
                                <button type="button" className="btn-close" onClick={() => { setShowAckModal(null); setAckNotes(''); }} disabled={actionLoading}></button>
                            </div>
                            <div className="modal-body">
                                <p>Confermi di aver letto e compreso questo training?</p>
                                <div className="mb-3">
                                    <label className="form-label">Note (opzionale)</label>
                                    <textarea className="form-control" rows="3" placeholder="Aggiungi un commento o una domanda..." value={ackNotes} onChange={(e) => setAckNotes(e.target.value)} disabled={actionLoading}></textarea>
                                </div>
                            </div>
                            <div className="modal-footer">
                                <button className="btn btn-light" onClick={() => { setShowAckModal(null); setAckNotes(''); }} disabled={actionLoading}>Annulla</button>
                                <button className="btn btn-success" onClick={() => handleAcknowledge(showAckModal)} disabled={actionLoading}>
                                    {actionLoading ? <><span className="spinner-border spinner-border-sm me-2"></span>Confermando...</> : <><i className="ri-check-line me-2"></i>Conferma</>}
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            )}

            <style>{`
                @keyframes fadeIn {
                    from { opacity: 0; transform: translateY(-10px); }
                    to { opacity: 1; transform: translateY(0); }
                }
            `}</style>

            <SupportWidget
                pageTitle="Formazione e Sviluppo"
                pageDescription="Gestisci la tua crescita professionale, visualizza i training assegnati e richiedi supporto formativo."
                pageIcon={FaGraduationCap}
                docsSection="formazione"
                onStartTour={() => setMostraTour(true)}
                brandName="Suite Clinica"
                logoSrc="/suitemind.png"
                accentColor="#6366F1"
            />

            <GuidedTour
                steps={tourSteps}
                isOpen={mostraTour}
                onClose={() => setMostraTour(false)}
                onComplete={() => {
                    setMostraTour(false);
                    console.log('Tour Formazione completato');
                }}
            />
        </>
    );
}

export default Formazione;

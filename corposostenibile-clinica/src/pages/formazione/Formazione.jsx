import { useState, useEffect, useCallback, useMemo } from 'react';
import { createPortal } from 'react-dom';
import { useOutletContext, useSearchParams } from 'react-router-dom';
import DatePicker from '../../components/DatePicker';
import trainingService from '../../services/trainingService';
import teamService, {
    ROLE_LABELS,
    SPECIALTY_LABELS,
    SPECIALTY_FILTER_OPTIONS,
} from '../../services/teamService';
import GuidedTour from '../../components/GuidedTour';
import SupportWidget from '../../components/SupportWidget';
import { getRequestedTourAudience, getTourContext } from '../../utils/tourScope';
import './Formazione.css';

// Colori sfondo header card in base alla specializzazione
const SPECIALTY_GRADIENTS = {
    nutrizione: 'linear-gradient(135deg, #22c55e 0%, #16a34a 100%)',
    nutrizionista: 'linear-gradient(135deg, #22c55e 0%, #16a34a 100%)',
    coach: 'linear-gradient(135deg, #f97316 0%, #ea580c 100%)',
    psicologia: 'linear-gradient(135deg, #ec4899 0%, #db2777 100%)',
    psicologo: 'linear-gradient(135deg, #ec4899 0%, #db2777 100%)',
};

const SPECIALTY_TEXT_COLORS = {
    nutrizione: '#16a34a', nutrizionista: '#16a34a',
    coach: '#ea580c',
    psicologia: '#db2777', psicologo: '#db2777',
};

const DEFAULT_GRADIENT = 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)';

// Tipi di training
const TRAINING_TYPES = {
    general: { label: 'Generale', color: '#6c757d' },
    performance: { label: 'Performance', color: '#0d6efd' },
    progetto: { label: 'Progetto', color: '#198754' },
    monthly: { label: 'Mensile', color: '#0dcaf0' },
    annual: { label: 'Annuale', color: '#6f42c1' },
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
    const [tourAudienceOverride, setTourAudienceOverride] = useState(null);
    const {
        isAdminOrCco: isAdmin,
        isRestrictedTeamLeader: isTeamLeader,
        specialtyMeta: tourSpecialtyMeta,
        isTeamLeaderTour: canManageTeamTrainingTour,
    } = getTourContext(user, tourAudienceOverride);
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
    const [adminTab, setAdminTab] = useState('myTrainings');
    const [adminView, setAdminView] = useState('professionals');
    const [professionals, setProfessionals] = useState([]);
    const [selectedProfessional, setSelectedProfessional] = useState(null);
    const [professionalTrainings, setProfessionalTrainings] = useState([]);
    const [adminFilters, setAdminFilters] = useState({ search: '', specialty: '' });
    const [currentPage, setCurrentPage] = useState(1);
    const ITEMS_PER_PAGE = 12;

    // ==================== USER STATE ====================
    const [activeTab, setActiveTab] = useState('trainings');
    const [trainings, setTrainings] = useState([]);
    const [givenTrainings, setGivenTrainings] = useState([]);
    const [requests, setRequests] = useState([]);
    const [receivedRequests, setReceivedRequests] = useState([]);
    const [recipients, setRecipients] = useState([]);

    // Tour
    const [mostraTour, setMostraTour] = useState(false);
    const [searchParams] = useSearchParams();
    const deepLinkTrainingId = parseInt(searchParams.get('trainingId') || '', 10);
    const deepLinkTrainingTab = searchParams.get('trainingTab');

    useEffect(() => {
        if (searchParams.get('startTour') === 'true') {
            const requestedAudience = getRequestedTourAudience(searchParams);
            if (requestedAudience) {
                setTourAudienceOverride(requestedAudience);
            }
            setMostraTour(true);
        }
    }, [searchParams]);

    const specialtyScopeLabel = tourSpecialtyMeta?.scopeLabel || 'area formativa';

    const tourSteps = useMemo(() => (canManageTeamTrainingTour ? [
        {
            target: '[data-tour="header"]',
            title: 'Formazione del Team',
            content: tourSpecialtyMeta
                ? `Qui non gestisci solo la tua crescita: controlli feedback, richieste e applicazione pratica del team nella ${specialtyScopeLabel}.`
                : 'Qui non gestisci solo la tua crescita: controlli feedback, richieste e applicazione pratica nel team.',
            placement: 'bottom',
            icon: <i className="ri-graduation-cap-line" style={{ fontSize: 18, color: '#fff' }} />,
            iconBg: 'linear-gradient(135deg, #6366F1, #8B5CF6)'
        },
        {
            target: '[data-tour="stats-cards"]',
            title: 'Cruscotto Formativo',
            content: tourSpecialtyMeta
                ? `Usa queste card per capire se il team della ${specialtyScopeLabel} sta leggendo i training e dove si accumulano richieste o gap.`
                : 'Usa queste card per capire se il team sta leggendo i training e dove si accumulano richieste o gap.',
            placement: 'bottom',
            icon: <i className="ri-bar-chart-2-line" style={{ fontSize: 18, color: '#fff' }} />,
            iconBg: 'linear-gradient(135deg, #3B82F6, #60A5FA)'
        },
        {
            target: '[data-tour="tabs-navigation"]',
            title: 'Flussi di Supervisione',
            content: tourSpecialtyMeta
                ? `Passa tra training assegnati, erogati e richieste per capire dove intervenire come reviewer o team leader della ${specialtyScopeLabel}.`
                : 'Passa tra training assegnati, erogati e richieste per capire dove intervenire come reviewer o team leader.',
            placement: 'bottom',
            icon: <i className="ri-filter-3-line" style={{ fontSize: 18, color: '#fff' }} />,
            iconBg: 'linear-gradient(135deg, #F59E0B, #FBBF24)'
        },
        {
            target: '[data-tour="content-list"]',
            title: 'Contenuti e Discussioni',
            content: tourSpecialtyMeta
                ? `Apri i training per verificare se il feedback e chiaro, letto e applicabile nel lavoro reale della ${specialtyScopeLabel}.`
                : 'Apri i training per verificare se il feedback e chiaro, letto e applicabile nel lavoro reale.',
            placement: 'top',
            icon: <i className="ri-list-check" style={{ fontSize: 18, color: '#fff' }} />,
            iconBg: 'linear-gradient(135deg, #10B981, #34D399)'
        },
        {
            target: '[data-tour="request-btn"]',
            title: 'Attiva Nuovo Training',
            content: tourSpecialtyMeta
                ? `Usa questo punto per aprire richieste o risposte formative quando emerge un gap concreto nella ${specialtyScopeLabel}.`
                : 'Usa questo punto per aprire richieste o risposte formative quando emerge un gap concreto nel team.',
            placement: 'left',
            icon: <i className="ri-add-circle-line" style={{ fontSize: 18, color: '#fff' }} />,
            iconBg: 'linear-gradient(135deg, #EC4899, #F472B6)'
        },
    ] : [
        {
            target: '[data-tour="header"]',
            title: 'Area Formazione',
            content: tourSpecialtyMeta
                ? `Qui puoi gestire il tuo percorso di crescita nella ${specialtyScopeLabel} e richiedere formazione specifica.`
                : 'Qui puoi gestire il tuo percorso di crescita professionale e richiedere formazione specifica.',
            placement: 'bottom',
            icon: <i className="ri-graduation-cap-line" style={{ fontSize: 18, color: '#fff' }} />,
            iconBg: 'linear-gradient(135deg, #6366F1, #8B5CF6)'
        },
        {
            target: '[data-tour="stats-cards"]',
            title: 'Dashboard Rapida',
            content: tourSpecialtyMeta
                ? `Tieni d occhio training ricevuti e stato delle tue richieste nella ${specialtyScopeLabel}.`
                : 'Tieni d occhio training ricevuti e stato delle tue richieste.',
            placement: 'bottom',
            icon: <i className="ri-bar-chart-2-line" style={{ fontSize: 18, color: '#fff' }} />,
            iconBg: 'linear-gradient(135deg, #3B82F6, #60A5FA)'
        },
        {
            target: '[data-tour="tabs-navigation"]',
            title: 'Organizzazione',
            content: tourSpecialtyMeta
                ? `Usa i tab per navigare tra training assegnati e richieste formazione della ${specialtyScopeLabel}.`
                : 'Usa i tab per navigare tra training assegnati e richieste formazione.',
            placement: 'bottom',
            icon: <i className="ri-filter-3-line" style={{ fontSize: 18, color: '#fff' }} />,
            iconBg: 'linear-gradient(135deg, #F59E0B, #FBBF24)'
        },
        {
            target: '[data-tour="content-list"]',
            title: 'I Tuoi Training',
            content: tourSpecialtyMeta
                ? `Clicca su un elemento per espandere i dettagli, leggere il feedback e confermare la presa visione nella ${specialtyScopeLabel}.`
                : 'Clicca su un elemento per espandere i dettagli, leggere il feedback e confermare la presa visione.',
            placement: 'top',
            icon: <i className="ri-list-check" style={{ fontSize: 18, color: '#fff' }} />,
            iconBg: 'linear-gradient(135deg, #10B981, #34D399)'
        },
        {
            target: '[data-tour="request-btn"]',
            title: 'Richiedi Formazione',
            content: tourSpecialtyMeta
                ? `Hai bisogno di supporto su un tema della ${specialtyScopeLabel}? Invia una richiesta di training al tuo responsabile o a un collega esperto.`
                : 'Hai bisogno di supporto su un tema specifico? Invia una richiesta di training al tuo responsabile o a un collega esperto.',
            placement: 'left',
            icon: <i className="ri-add-circle-line" style={{ fontSize: 18, color: '#fff' }} />,
            iconBg: 'linear-gradient(135deg, #EC4899, #F472B6)'
        },
    ]), [canManageTeamTrainingTour, specialtyScopeLabel, tourSpecialtyMeta]);

    // Pagination per sezioni
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

    // Nuovo training
    const [showNewTrainingModal, setShowNewTrainingModal] = useState(false);
    const [newTraining, setNewTraining] = useState({
        title: '', content: '', review_type: 'feedback',
        strengths: '', improvements: '', goals: '',
        period_start: '', period_end: '',
    });

    // Lazy loading state
    const [recipientsLoaded, setRecipientsLoaded] = useState(false);
    const [recipientsLoading, setRecipientsLoading] = useState(false);
    const [teamLoaded, setTeamLoaded] = useState(false);
    const [teamLoading, setTeamLoading] = useState(false);

    // ==================== CALLBACKS ====================
    const fetchData = useCallback(async () => {
        try {
            setLoading(true);
            setError(null);
            if (canManageTeamTraining) {
                const [trainingsRes, givenRes, requestsRes, receivedRes] = await Promise.all([
                    trainingService.getMyTrainings(),
                    trainingService.getGivenTrainings(),
                    trainingService.getMyRequests(),
                    trainingService.getReceivedRequests(),
                ]);
                setTrainings(trainingsRes.trainings || []);
                setGivenTrainings(givenRes.trainings || []);
                setRequests(requestsRes.requests || []);
                setReceivedRequests(receivedRes.requests || []);
            } else {
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
    useEffect(() => { fetchData(); }, [fetchData]);

    useEffect(() => {
        if (showRequestModal && !recipientsLoaded) loadRecipients();
    }, [showRequestModal, recipientsLoaded, loadRecipients]);

    useEffect(() => {
        if (adminTab === 'team' && canManageTeamTraining && !teamLoaded) loadTeamMembers();
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
        if (!Number.isInteger(deepLinkTrainingId) || deepLinkTrainingId <= 0 || loading) return;
        const inTrainings = trainings.some(t => t.id === deepLinkTrainingId);
        const inGivenTrainings = givenTrainings.some(t => t.id === deepLinkTrainingId);
        let targetTab = deepLinkTrainingTab === 'given' ? 'given' : 'trainings';
        if (targetTab === 'given' && !inGivenTrainings && inTrainings) targetTab = 'trainings';
        if (targetTab === 'trainings' && !inTrainings && inGivenTrainings) targetTab = 'given';
        if (!inTrainings && !inGivenTrainings) return;
        if (activeTab !== targetTab) setActiveTab(targetTab);
        if (expandedTraining !== deepLinkTrainingId) setExpandedTraining(deepLinkTrainingId);
    }, [deepLinkTrainingId, deepLinkTrainingTab, loading, trainings, givenTrainings, activeTab, expandedTraining]);

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
        setAdminTab('team');
    };

    const handleAdminFilterChange = (key, value) => {
        setAdminFilters(prev => ({ ...prev, [key]: value }));
        setCurrentPage(1);
    };

    const resetAdminFilters = () => {
        setAdminFilters({ search: '', specialty: isTeamLeader ? teamLeaderSpecialtyFilterValue : '' });
        setCurrentPage(1);
    };

    const filteredProfessionals = professionals.filter(p => {
        const searchLower = adminFilters.search.toLowerCase();
        const matchesSearch = !adminFilters.search || (
            p.firstName?.toLowerCase().includes(searchLower) ||
            p.lastName?.toLowerCase().includes(searchLower) ||
            p.email?.toLowerCase().includes(searchLower) ||
            p.department?.toLowerCase().includes(searchLower) ||
            p.jobTitle?.toLowerCase().includes(searchLower)
        );
        const matchesSpecialty = !adminFilters.specialty ||
            adminFilters.specialty.split(',').some(spec => p.specialty === spec.trim());
        const isHM = p.specialty === 'health_manager' || p.role === 'health_manager';
        return matchesSearch && matchesSpecialty && !isHM;
    });

    const totalPages = Math.ceil(filteredProfessionals.length / ITEMS_PER_PAGE);
    const paginatedProfessionals = filteredProfessionals.slice(
        (currentPage - 1) * ITEMS_PER_PAGE,
        currentPage * ITEMS_PER_PAGE
    );

    const allowedSpecialtyFilterOptions = isTeamLeader && teamLeaderSpecialtyGroup
        ? SPECIALTY_FILTER_OPTIONS.filter((opt) => {
            const values = String(opt.value || '').split(',').map(v => v.trim());
            return values.includes(teamLeaderSpecialtyGroup);
        })
        : SPECIALTY_FILTER_OPTIONS;

    // ==================== USER FUNCTIONS ====================
    const stats = {
        totalTrainings: trainings.length,
        unacknowledged: trainings.filter(t => !t.isAcknowledged && !t.isDraft).length,
        unreadMessages: trainings.reduce((sum, t) => sum + (t.unreadCount || 0), 0),
        totalGiven: givenTrainings.length,
        givenPending: givenTrainings.filter(t => !t.isAcknowledged && !t.isDraft).length,
        givenAcknowledged: givenTrainings.filter(t => t.isAcknowledged).length,
        pendingRequests: requests.filter(r => r.status === 'pending').length,
        acceptedRequests: requests.filter(r => r.status === 'accepted').length,
        completedRequests: requests.filter(r => r.status === 'completed').length,
        rejectedRequests: requests.filter(r => r.status === 'rejected').length,
        receivedPending: receivedRequests.filter(r => r.status === 'pending').length,
        receivedAccepted: receivedRequests.filter(r => r.status === 'accepted').length,
        receivedTotal: receivedRequests.length,
    };

    const normalizedSearch = listSearch.trim().toLowerCase();
    const filterBySearch = (value) => (value || '').toLowerCase().includes(normalizedSearch);

    const filteredTrainings = trainings.filter((t) => {
        if (!normalizedSearch) return true;
        return filterBySearch(t.title) || filterBySearch(t.content) || filterBySearch(t.reviewType) ||
            filterBySearch(`${t.reviewer?.firstName || ''} ${t.reviewer?.lastName || ''}`);
    });

    const filteredGivenTrainings = givenTrainings.filter((t) => {
        if (!normalizedSearch) return true;
        return filterBySearch(t.title) || filterBySearch(t.content) || filterBySearch(t.reviewType) ||
            filterBySearch(`${t.reviewee?.firstName || ''} ${t.reviewee?.lastName || ''}`);
    });

    const filteredRequests = requests.filter((r) => {
        if (!normalizedSearch) return true;
        return filterBySearch(r.subject) || filterBySearch(r.description) || filterBySearch(r.priority) ||
            filterBySearch(r.status) || filterBySearch(`${r.requestedTo?.firstName || ''} ${r.requestedTo?.lastName || ''}`);
    });

    const filteredReceivedRequests = receivedRequests.filter((r) => {
        if (!normalizedSearch) return true;
        return filterBySearch(r.subject) || filterBySearch(r.description) || filterBySearch(r.priority) ||
            filterBySearch(r.status) || filterBySearch(`${r.requester?.firstName || ''} ${r.requester?.lastName || ''}`);
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
        return new Date(dateStr).toLocaleDateString('it-IT', {
            day: 'numeric', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit'
        });
    };

    const handleAcknowledge = async (trainingId) => {
        try {
            setActionLoading(true);
            await trainingService.acknowledgeTraining(trainingId, ackNotes);
            setTrainings(prev => prev.map(t =>
                t.id === trainingId ? { ...t, isAcknowledged: true, acknowledgedAt: new Date().toISOString(), acknowledgmentNotes: ackNotes } : t
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
                        ? { ...t, messages: [...(t.messages || []), { id: response.message.id, senderId: response.message.senderId, senderName: response.message.senderName, content: response.message.content, createdAt: response.message.createdAt, isOwn: true }] }
                        : t
                ));
            }
            setNewMessage('');
        } catch (err) {
            console.error('Errore invio messaggio:', err);
            alert(err.response?.data?.error || "Errore nell'invio del messaggio");
        } finally {
            setActionLoading(false);
        }
    };

    const handleCreateRequest = async () => {
        if (!newRequest.subject.trim()) return;
        if (!newRequest.recipient_id) { alert('Seleziona un destinatario'); return; }
        try {
            setActionLoading(true);
            const response = await trainingService.createRequest({
                subject: newRequest.subject, description: newRequest.description,
                priority: newRequest.priority, recipient_id: parseInt(newRequest.recipient_id),
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
        if (!request?.id || !['accept', 'reject'].includes(action)) return;
        try {
            setRequestResponseLoadingId(request.id);
            const responseNotes = (requestResponseDrafts[request.id] || '').trim();
            const res = await trainingService.respondToRequest(request.id, { action, response_notes: responseNotes });
            if (res?.success) {
                setReceivedRequests(prev => prev.map(r => (
                    r.id === request.id
                        ? { ...r, status: res.request?.status || (action === 'accept' ? 'accepted' : 'rejected'), respondedAt: res.request?.respondedAt || new Date().toISOString(), responseNotes: res.request?.responseNotes ?? responseNotes, reviewId: res.request?.reviewId ?? r.reviewId }
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
            const prof = { id: request.requester.id, firstName: request.requester.firstName || '', lastName: request.requester.lastName || '' };
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
        if (!newTraining.title.trim()) { alert('Inserisci un titolo'); return; }
        if (!newTraining.content.trim()) { alert('Inserisci il contenuto del training'); return; }
        if (!selectedProfessional?.id) { alert('Nessun professionista selezionato'); return; }
        try {
            setActionLoading(true);
            const response = await trainingService.createTrainingForUser(selectedProfessional.id, {
                title: newTraining.title, content: newTraining.content, review_type: newTraining.review_type,
                strengths: newTraining.strengths, improvements: newTraining.improvements, goals: newTraining.goals,
                period_start: newTraining.period_start || null, period_end: newTraining.period_end || null,
            });
            if (response.success) {
                const res = await trainingService.getAdminUserTrainings(selectedProfessional.id);
                setProfessionalTrainings(res.trainings || []);
                setNewTraining({ title: '', content: '', review_type: 'feedback', strengths: '', improvements: '', goals: '', period_start: '', period_end: '' });
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
            setTrainings(prev => prev.map(t => t.id === trainingId ? { ...t, unreadCount: 0 } : t));
        } catch (err) {
            console.error('Errore mark all read:', err);
        }
    };

    useEffect(() => {
        if (expandedTraining && !isAdmin) {
            const training = trainings.find(t => t.id === expandedTraining);
            if (training && training.unreadCount > 0) handleMarkAllRead(expandedTraining);
        }
    }, [expandedTraining, trainings, isAdmin]);

    // ==================== SHARED RENDER HELPERS ====================

    /** Render a single training row (used across all views) */
    const renderTrainingRow = (training, { showReviewer = true, showReviewee = false, showMessages = true, isAdminReadOnly = false } = {}) => (
        <div key={training.id} className="frm-list-item">
            <div
                className={`frm-list-item-header${expandedTraining === training.id ? ' expanded' : ''}`}
                onClick={() => setExpandedTraining(expandedTraining === training.id ? null : training.id)}
            >
                <div style={{ flex: 1, minWidth: 0 }}>
                    <div className="frm-list-item-title">
                        {training.title}
                        <i className={`ri-arrow-${expandedTraining === training.id ? 'up' : 'down'}-s-line`} />
                    </div>
                    <div className="frm-list-item-meta">
                        {showReviewer && <span><i className="ri-user-line" />{training.reviewer?.firstName} {training.reviewer?.lastName}</span>}
                        {showReviewee && <span><i className="ri-user-received-line" />A: {training.reviewee?.firstName} {training.reviewee?.lastName}</span>}
                        <span><i className="ri-calendar-line" />{formatDate(training.createdAt)}</span>
                    </div>
                </div>
                <div className="frm-list-item-badges">
                    <span className="frm-badge" style={{ background: `${TRAINING_TYPES[training.reviewType]?.color || '#6c757d'}18`, color: TRAINING_TYPES[training.reviewType]?.color || '#6c757d' }}>
                        {TRAINING_TYPES[training.reviewType]?.label || training.reviewType}
                    </span>
                    {training.isDraft && <span className="frm-badge secondary"><i className="ri-draft-line" />Bozza</span>}
                    {training.isAcknowledged ? (
                        <span className="frm-badge success"><i className="ri-check-line" />Confermato</span>
                    ) : !training.isDraft && (
                        <span className="frm-badge warning">Da confermare</span>
                    )}
                    {!isAdminReadOnly && training.unreadCount > 0 && (
                        <span className="frm-badge danger"><i className="ri-message-3-line" />{training.unreadCount}</span>
                    )}
                </div>
            </div>

            {expandedTraining === training.id && (
                <div className="frm-expanded-content">
                    {(training.periodStart || training.periodEnd) && (
                        <div className="frm-list-item-meta" style={{ marginBottom: 12 }}>
                            <span><i className="ri-calendar-2-line" />Periodo: {training.periodStart || '-'} — {training.periodEnd || '-'}</span>
                        </div>
                    )}

                    <div className="frm-content-block"><p>{training.content}</p></div>

                    {training.strengths && (
                        <div className="frm-highlight-block strengths">
                            <h6 className="text-success"><i className="ri-thumb-up-line me-2" />Punti di Forza</h6>
                            <p>{training.strengths}</p>
                        </div>
                    )}
                    {training.improvements && (
                        <div className="frm-highlight-block improvements">
                            <h6 style={{ color: '#92400e' }}><i className="ri-lightbulb-line me-2" />Aree di Miglioramento</h6>
                            <p>{training.improvements}</p>
                        </div>
                    )}
                    {training.goals && (
                        <div className="frm-highlight-block goals">
                            <h6 className="text-primary"><i className="ri-focus-3-line me-2" />Obiettivi</h6>
                            <p>{training.goals}</p>
                        </div>
                    )}

                    {/* Acknowledgment status */}
                    {training.isAcknowledged ? (
                        <div className="frm-alert success">
                            <i className="ri-check-double-line" style={{ fontSize: 20 }} />
                            <div className="frm-alert-content">
                                <strong>{isAdminReadOnly ? 'Confermato dal destinatario' : 'Confermato'}</strong>
                                <span className="ms-2" style={{ fontSize: 12, opacity: 0.7 }}>il {formatDateTime(training.acknowledgedAt)}</span>
                                {training.acknowledgmentNotes && <p style={{ margin: '4px 0 0', fontSize: 13 }}>{training.acknowledgmentNotes}</p>}
                            </div>
                        </div>
                    ) : !training.isDraft && !isAdminReadOnly ? (
                        <div className="frm-alert warning" style={{ justifyContent: 'space-between', flexWrap: 'wrap', gap: 8 }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                                <i className="ri-information-line" />
                                <strong>Conferma di aver letto questo training</strong>
                            </div>
                            <button className="frm-btn-primary" style={{ padding: '6px 14px' }} onClick={(e) => { e.stopPropagation(); setShowAckModal(training.id); }} disabled={actionLoading}>
                                <i className="ri-check-line" />Conferma
                            </button>
                        </div>
                    ) : !training.isDraft && (
                        <div className="frm-alert warning">
                            <i className="ri-time-line" />
                            <strong>In attesa di conferma</strong>
                        </div>
                    )}

                    {/* Discussion */}
                    {showMessages && !isAdminReadOnly && (
                        <div className="frm-chat-wrap">
                            <h6><i className="ri-chat-3-line me-2" />Discussione</h6>
                            <div className="frm-chat-messages" style={{ minHeight: (training.messages?.length || 0) > 0 ? '80px' : '0' }}>
                                {(!training.messages || training.messages.length === 0) ? (
                                    <p style={{ textAlign: 'center', color: 'var(--frm-text-light)', fontSize: 13, padding: '12px 0' }}>Nessun messaggio. Inizia la discussione!</p>
                                ) : (
                                    training.messages.map(msg => (
                                        <div key={msg.id} className={`frm-chat-bubble ${msg.isOwn ? 'own' : 'other'}`}>
                                            <div className="frm-chat-bubble-header">
                                                <strong>{msg.senderName}</strong>
                                                <span>{formatDate(msg.createdAt)}</span>
                                            </div>
                                            <p style={{ margin: 0, fontSize: 13 }}>{msg.content}</p>
                                        </div>
                                    ))
                                )}
                            </div>
                            <div className="frm-chat-input">
                                <input
                                    type="text" placeholder="Scrivi un messaggio..." value={newMessage}
                                    onChange={(e) => setNewMessage(e.target.value)}
                                    onKeyPress={(e) => { if (e.key === 'Enter' && !actionLoading) handleSendMessage(training.id); }}
                                    onClick={(e) => e.stopPropagation()} disabled={actionLoading}
                                />
                                <button onClick={(e) => { e.stopPropagation(); handleSendMessage(training.id); }} disabled={actionLoading || !newMessage.trim()}>
                                    {actionLoading ? <span className="frm-spinner" style={{ width: 16, height: 16, borderWidth: 2 }} /> : <i className="ri-send-plane-line" />}
                                </button>
                            </div>
                        </div>
                    )}

                    {/* Admin read-only messages */}
                    {isAdminReadOnly && training.messages && training.messages.length > 0 && (
                        <div className="frm-chat-wrap">
                            <h6><i className="ri-chat-3-line me-2" />Discussione ({training.messages.length} messaggi)</h6>
                            <div className="frm-chat-messages">
                                {training.messages.map(msg => (
                                    <div key={msg.id} className="frm-chat-bubble other">
                                        <div className="frm-chat-bubble-header">
                                            <strong>{msg.senderName}</strong>
                                            <span>{formatDate(msg.createdAt)}</span>
                                        </div>
                                        <p style={{ margin: 0, fontSize: 13 }}>{msg.content}</p>
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}
                </div>
            )}
        </div>
    );

    /** Render a pagination block */
    const renderPagination = (items, page, setPage) => {
        if (items.length <= ITEMS_PER_SECTION) return null;
        const tp = Math.ceil(items.length / ITEMS_PER_SECTION);
        return (
            <div className="form-pagination">
                <span className="form-pagination-info">
                    {Math.min((page - 1) * ITEMS_PER_SECTION + 1, items.length)}–{Math.min(page * ITEMS_PER_SECTION, items.length)} di {items.length}
                </span>
                <div className="form-pagination-buttons">
                    <button className="form-page-btn" disabled={page === 1} onClick={() => setPage(p => Math.max(1, p - 1))}>&laquo;</button>
                    {Array.from({ length: tp }, (_, i) => i + 1)
                        .filter(p => p >= Math.max(1, page - 2) && p <= Math.min(tp, page + 2))
                        .map(p => (
                            <button key={p} className={`form-page-btn${page === p ? ' active' : ''}`} onClick={() => setPage(p)}>{p}</button>
                        ))}
                    <button className="form-page-btn" disabled={page >= tp} onClick={() => setPage(p => Math.min(tp, p + 1))}>&raquo;</button>
                </div>
            </div>
        );
    };

    /** Render a request row */
    const renderRequestRow = (request, { isSent = false } = {}) => (
        <div key={request.id} className="frm-list-item">
            <div
                className={`frm-list-item-header${expandedRequest === request.id ? ' expanded' : ''}`}
                onClick={() => setExpandedRequest(expandedRequest === request.id ? null : request.id)}
            >
                <div style={{ flex: 1, minWidth: 0 }}>
                    <div className="frm-list-item-title">
                        {request.subject}
                        <i className={`ri-arrow-${expandedRequest === request.id ? 'up' : 'down'}-s-line`} />
                    </div>
                    <div className="frm-list-item-meta">
                        <span>
                            <i className="ri-user-line" />
                            {isSent
                                ? `A: ${request.requestedTo?.firstName} ${request.requestedTo?.lastName}`
                                : `Da: ${request.requester?.firstName} ${request.requester?.lastName}`
                            }
                        </span>
                        <span><i className="ri-calendar-line" />{formatDate(request.createdAt)}</span>
                    </div>
                </div>
                <div className="frm-list-item-badges">
                    <span className="frm-badge" style={{ background: `${PRIORITIES[request.priority]?.color || '#6c757d'}18`, color: PRIORITIES[request.priority]?.color || '#6c757d' }}>
                        {PRIORITIES[request.priority]?.label || request.priority}
                    </span>
                    {request.status === 'pending' && <span className="frm-badge warning"><i className="ri-time-line" />{isSent ? 'In Attesa' : 'Da gestire'}</span>}
                    {request.status === 'accepted' && <span className="frm-badge info"><i className="ri-check-line" />{isSent ? 'In Preparazione' : 'Accettata'}</span>}
                    {request.status === 'completed' && <span className="frm-badge success"><i className="ri-check-double-line" />Completata</span>}
                    {request.status === 'rejected' && <span className="frm-badge danger"><i className="ri-close-line" />Rifiutata</span>}
                </div>
            </div>

            {expandedRequest === request.id && (
                <div className="frm-expanded-content">
                    {request.description && (
                        <div className={`frm-highlight-block ${isSent ? 'goals' : 'request-desc'}`}>
                            <h6><i className="ri-file-text-line me-2" />{isSent ? 'Descrizione' : 'Descrizione Richiesta'}</h6>
                            <p>{request.description}</p>
                        </div>
                    )}

                    {/* === SENT REQUEST STATUS === */}
                    {isSent && request.status === 'pending' && (
                        <>
                            <div className="frm-alert warning">
                                <i className="ri-time-line" />
                                <div className="frm-alert-content">
                                    <strong>In attesa di risposta</strong>
                                    <p style={{ margin: '4px 0 0', fontSize: 12 }}>La tua richiesta è stata inviata e verrà esaminata al più presto.</p>
                                </div>
                            </div>
                            <button className="frm-btn-secondary" style={{ color: '#dc3545', borderColor: '#fecaca' }} onClick={(e) => { e.stopPropagation(); handleCancelRequest(request.id); }} disabled={actionLoading}>
                                {actionLoading ? <span className="frm-spinner" style={{ width: 14, height: 14, borderWidth: 2 }} /> : <i className="ri-delete-bin-line" />}
                                Cancella Richiesta
                            </button>
                        </>
                    )}
                    {isSent && request.status === 'accepted' && (
                        <div className="frm-alert info">
                            <i className="ri-check-line" />
                            <div className="frm-alert-content">
                                <strong>Richiesta accettata</strong>
                                <p style={{ margin: '4px 0 0', fontSize: 12 }}>Il training è in preparazione.{request.respondedAt && <span> Accettata il {formatDateTime(request.respondedAt)}</span>}</p>
                                {request.responseNotes && <div style={{ marginTop: 6, padding: '6px 10px', background: 'rgba(255,255,255,0.5)', borderRadius: 6, fontSize: 13 }}><strong>Note:</strong> {request.responseNotes}</div>}
                            </div>
                        </div>
                    )}
                    {isSent && request.status === 'completed' && (
                        <div className="frm-alert success" style={{ justifyContent: 'space-between', flexWrap: 'wrap' }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                                <i className="ri-check-double-line" />
                                <strong>Training Completato!</strong>
                            </div>
                            {request.reviewId && (
                                <button className="frm-btn-primary" style={{ padding: '5px 12px', fontSize: 12 }} onClick={(e) => { e.stopPropagation(); setExpandedTraining(request.reviewId); setActiveTab('trainings'); }}>
                                    <i className="ri-eye-line" />Visualizza
                                </button>
                            )}
                        </div>
                    )}
                    {isSent && request.status === 'rejected' && (
                        <>
                            <div className="frm-alert danger">
                                <i className="ri-close-circle-line" />
                                <div className="frm-alert-content">
                                    <strong>Richiesta Rifiutata</strong>
                                    {request.respondedAt && <span style={{ fontSize: 12, marginLeft: 8 }}>il {formatDateTime(request.respondedAt)}</span>}
                                </div>
                            </div>
                            {request.responseNotes && (
                                <div className="frm-highlight-block rejected">
                                    <h6 style={{ color: '#991b1b' }}><i className="ri-feedback-line me-2" />Motivazione</h6>
                                    <p>{request.responseNotes}</p>
                                </div>
                            )}
                        </>
                    )}

                    {/* === RECEIVED REQUEST STATUS === */}
                    {!isSent && request.status === 'pending' && (
                        <>
                            <div className="frm-alert info">
                                <i className="ri-information-line" />
                                <div className="frm-alert-content">
                                    <strong>Questa richiesta è in attesa di risposta.</strong>
                                    <p style={{ margin: '4px 0 0', fontSize: 12 }}>Gestisci questa richiesta: accettazione/risposta e creazione training.</p>
                                </div>
                            </div>
                            <div className="frm-response-wrap">
                                <label><i className="ri-chat-3-line" />Risposta / Note al collega</label>
                                <textarea
                                    rows="3"
                                    placeholder="Scrivi una risposta rapida (es. ok, creo il training oggi / ci sentiamo in call / ecc.)"
                                    value={requestResponseDrafts[request.id] ?? (request.responseNotes || '')}
                                    onChange={(e) => setRequestResponseDrafts(prev => ({ ...prev, [request.id]: e.target.value }))}
                                    onClick={(e) => e.stopPropagation()}
                                    disabled={requestResponseLoadingId === request.id}
                                />
                                <div className="frm-response-actions">
                                    <button className="frm-btn-primary" onClick={(e) => { e.stopPropagation(); handleRespondToReceivedRequest(request, 'accept'); }} disabled={requestResponseLoadingId === request.id}>
                                        {requestResponseLoadingId === request.id ? <span className="frm-spinner" style={{ width: 14, height: 14, borderWidth: 2 }} /> : <i className="ri-check-line" />}
                                        Accetta
                                    </button>
                                    <button className="frm-btn-secondary" style={{ color: '#dc3545', borderColor: '#fecaca' }} onClick={(e) => { e.stopPropagation(); handleRespondToReceivedRequest(request, 'reject'); }} disabled={requestResponseLoadingId === request.id}>
                                        <i className="ri-close-line" />Rifiuta
                                    </button>
                                </div>
                            </div>
                        </>
                    )}
                    {!isSent && request.status === 'completed' && request.reviewId && (
                        <div className="frm-alert success">
                            <i className="ri-check-double-line" /><strong>Training completato!</strong>
                        </div>
                    )}
                    {!isSent && request.status === 'accepted' && (
                        <div className="frm-alert primary" style={{ justifyContent: 'space-between', flexWrap: 'wrap', gap: 8 }}>
                            <div className="frm-alert-content">
                                <strong>Richiesta accettata</strong>
                                {request.respondedAt && <span style={{ fontSize: 12, marginLeft: 8 }}>il {formatDateTime(request.respondedAt)}</span>}
                                {request.responseNotes && <div style={{ marginTop: 4, fontSize: 13 }}><strong>Risposta:</strong> {request.responseNotes}</div>}
                            </div>
                            <button className="frm-btn-primary" style={{ padding: '5px 12px', fontSize: 12 }} onClick={(e) => { e.stopPropagation(); handleOpenTrainingFromRequest(request); }} disabled={actionLoading}>
                                <i className="ri-edit-line" />Scrivi Training
                            </button>
                        </div>
                    )}
                    {!isSent && request.status === 'rejected' && request.responseNotes && (
                        <div className="frm-alert danger">
                            <i className="ri-chat-3-line" />
                            <div className="frm-alert-content">
                                <strong>Risposta inviata</strong>
                                <div style={{ marginTop: 4, fontSize: 13 }}>{request.responseNotes}</div>
                            </div>
                        </div>
                    )}
                </div>
            )}
        </div>
    );

    /** Render an empty state */
    const renderEmpty = (icon, title, subtitle, action) => (
        <div className="frm-empty">
            <div className="frm-empty-icon"><i className={icon} /></div>
            <h5>{title}</h5>
            <p>{subtitle}</p>
            {action}
        </div>
    );

    /** Render Acknowledge Modal */
    const renderAckModal = () => {
        if (!showAckModal) return null;
        return createPortal(
            <div className="frm-modal-backdrop" onClick={() => { setShowAckModal(null); setAckNotes(''); }}>
                <div className="frm-modal" onClick={e => e.stopPropagation()}>
                    <div className="frm-modal-header">
                        <h5><i className="ri-check-double-line" style={{ color: '#25B36A' }} />Conferma Lettura</h5>
                        <button className="frm-modal-close" onClick={() => { setShowAckModal(null); setAckNotes(''); }} disabled={actionLoading}>
                            <i className="ri-close-line" />
                        </button>
                    </div>
                    <div className="frm-modal-body">
                        <p style={{ color: 'var(--frm-text-secondary)', marginBottom: 16 }}>Confermi di aver letto e compreso questo training?</p>
                        <div className="frm-form-group">
                            <label>Note (opzionale)</label>
                            <textarea rows="3" placeholder="Aggiungi un commento o una domanda..." value={ackNotes} onChange={(e) => setAckNotes(e.target.value)} disabled={actionLoading} />
                        </div>
                    </div>
                    <div className="frm-modal-footer">
                        <button className="frm-btn-secondary" onClick={() => { setShowAckModal(null); setAckNotes(''); }} disabled={actionLoading}>Annulla</button>
                        <button className="frm-btn-primary" onClick={() => handleAcknowledge(showAckModal)} disabled={actionLoading}>
                            {actionLoading ? <><span className="frm-spinner" style={{ width: 14, height: 14, borderWidth: 2 }} />Confermando...</> : <><i className="ri-check-line" />Conferma</>}
                        </button>
                    </div>
                </div>
            </div>,
            document.body
        );
    };

    /** Render Request Training Modal */
    const renderRequestModal = () => {
        if (!showRequestModal) return null;
        return createPortal(
            <div className="frm-modal-backdrop" onClick={() => setShowRequestModal(false)}>
                <div className="frm-modal" onClick={e => e.stopPropagation()}>
                    <div className="frm-modal-header">
                        <h5><i className="ri-add-circle-line" style={{ color: '#25B36A' }} />Richiedi Training</h5>
                        <button className="frm-modal-close" onClick={() => setShowRequestModal(false)} disabled={actionLoading}>
                            <i className="ri-close-line" />
                        </button>
                    </div>
                    <div className="frm-modal-body">
                        <div className="frm-form-group">
                            <label>Destinatario *</label>
                            <select value={newRequest.recipient_id} onChange={(e) => setNewRequest(prev => ({ ...prev, recipient_id: e.target.value }))} disabled={actionLoading || recipientsLoading}>
                                <option value="">Seleziona un destinatario...</option>
                                {recipients.map(r => <option key={r.id} value={r.id}>{r.name} {r.role ? `- ${r.role}` : ''} {r.department ? `(${r.department})` : ''}</option>)}
                            </select>
                            {recipientsLoading && <small style={{ color: 'var(--frm-text-light)', marginTop: 6, display: 'block', fontSize: 12 }}>Caricamento destinatari...</small>}
                            {!recipientsLoading && recipientsLoaded && recipients.length === 0 && <small style={{ color: '#dc3545', marginTop: 6, display: 'block', fontSize: 12 }}>Nessun destinatario disponibile.</small>}
                        </div>
                        <div className="frm-form-group">
                            <label>Argomento *</label>
                            <input type="text" placeholder="Es: Gestione pazienti diabetici" value={newRequest.subject} onChange={(e) => setNewRequest(prev => ({ ...prev, subject: e.target.value }))} disabled={actionLoading} />
                        </div>
                        <div className="frm-form-group">
                            <label>Descrizione</label>
                            <textarea rows="4" placeholder="Descrivi cosa vorresti approfondire..." value={newRequest.description} onChange={(e) => setNewRequest(prev => ({ ...prev, description: e.target.value }))} disabled={actionLoading} />
                        </div>
                        <div className="frm-form-group">
                            <label>Priorità</label>
                            <select value={newRequest.priority} onChange={(e) => setNewRequest(prev => ({ ...prev, priority: e.target.value }))} disabled={actionLoading}>
                                <option value="low">Bassa</option>
                                <option value="normal">Normale</option>
                                <option value="high">Alta</option>
                                <option value="urgent">Urgente</option>
                            </select>
                        </div>
                    </div>
                    <div className="frm-modal-footer">
                        <button className="frm-btn-secondary" onClick={() => setShowRequestModal(false)} disabled={actionLoading}>Annulla</button>
                        <button className="frm-btn-primary" onClick={handleCreateRequest} disabled={!newRequest.subject.trim() || !newRequest.recipient_id || actionLoading}>
                            {actionLoading ? <><span className="frm-spinner" style={{ width: 14, height: 14, borderWidth: 2 }} />Invio...</> : <><i className="ri-send-plane-line" />Invia Richiesta</>}
                        </button>
                    </div>
                </div>
            </div>,
            document.body
        );
    };

    /** Render New Training Modal */
    const renderNewTrainingModal = () => {
        if (!showNewTrainingModal || !selectedProfessional) return null;
        return createPortal(
            <div className="frm-modal-backdrop" onClick={() => setShowNewTrainingModal(false)}>
                <div className="frm-modal lg" onClick={e => e.stopPropagation()}>
                    <div className="frm-modal-header">
                        <h5><i className="ri-edit-line" style={{ color: '#25B36A' }} />Nuovo Training per {selectedProfessional.firstName} {selectedProfessional.lastName}</h5>
                        <button className="frm-modal-close" onClick={() => setShowNewTrainingModal(false)} disabled={actionLoading}>
                            <i className="ri-close-line" />
                        </button>
                    </div>
                    <div className="frm-modal-body">
                        <div className="frm-form-group">
                            <label>Titolo *</label>
                            <input type="text" placeholder="Es: Feedback trimestrale Q1 2025" value={newTraining.title} onChange={(e) => setNewTraining(prev => ({ ...prev, title: e.target.value }))} disabled={actionLoading} />
                        </div>
                        <div className="frm-form-group">
                            <div className="frm-form-row">
                                <div>
                                    <label>Tipo</label>
                                    <select value={newTraining.review_type} onChange={(e) => setNewTraining(prev => ({ ...prev, review_type: e.target.value }))} disabled={actionLoading}>
                                        <option value="general">Generale</option>
                                        <option value="performance">Performance</option>
                                        <option value="progetto">Progetto</option>
                                        <option value="monthly">Mensile</option>
                                        <option value="annual">Annuale</option>
                                    </select>
                                </div>
                                <div>
                                    <label>Periodo Inizio</label>
                                    <DatePicker value={newTraining.period_start} onChange={(e) => setNewTraining(prev => ({ ...prev, period_start: e.target.value }))} disabled={actionLoading} />
                                </div>
                                <div>
                                    <label>Periodo Fine</label>
                                    <DatePicker value={newTraining.period_end} onChange={(e) => setNewTraining(prev => ({ ...prev, period_end: e.target.value }))} disabled={actionLoading} />
                                </div>
                            </div>
                        </div>
                        <div className="frm-form-group">
                            <label>Contenuto del Training *</label>
                            <textarea rows="5" placeholder="Descrivi il feedback generale, le attività svolte, i risultati raggiunti..." value={newTraining.content} onChange={(e) => setNewTraining(prev => ({ ...prev, content: e.target.value }))} disabled={actionLoading} />
                        </div>
                        <div className="frm-form-group">
                            <label style={{ color: '#16a34a' }}><i className="ri-thumb-up-line me-1" />Punti di Forza</label>
                            <textarea rows="3" placeholder="Quali sono i punti di forza dimostrati?" value={newTraining.strengths} onChange={(e) => setNewTraining(prev => ({ ...prev, strengths: e.target.value }))} disabled={actionLoading} style={{ borderColor: '#dcfce7' }} />
                        </div>
                        <div className="frm-form-group">
                            <label style={{ color: '#d97706' }}><i className="ri-lightbulb-line me-1" />Aree di Miglioramento</label>
                            <textarea rows="3" placeholder="Su cosa dovrebbe lavorare?" value={newTraining.improvements} onChange={(e) => setNewTraining(prev => ({ ...prev, improvements: e.target.value }))} disabled={actionLoading} style={{ borderColor: '#fef3c7' }} />
                        </div>
                        <div className="frm-form-group">
                            <label style={{ color: '#2563eb' }}><i className="ri-focus-3-line me-1" />Obiettivi</label>
                            <textarea rows="3" placeholder="Quali sono gli obiettivi per il prossimo periodo?" value={newTraining.goals} onChange={(e) => setNewTraining(prev => ({ ...prev, goals: e.target.value }))} disabled={actionLoading} style={{ borderColor: '#dbeafe' }} />
                        </div>
                    </div>
                    <div className="frm-modal-footer">
                        <button className="frm-btn-secondary" onClick={() => setShowNewTrainingModal(false)} disabled={actionLoading}>Annulla</button>
                        <button className="frm-btn-primary" onClick={handleCreateTraining} disabled={!newTraining.title.trim() || !newTraining.content.trim() || actionLoading}>
                            {actionLoading ? <><span className="frm-spinner" style={{ width: 14, height: 14, borderWidth: 2 }} />Salvataggio...</> : <><i className="ri-save-line" />Salva Training</>}
                        </button>
                    </div>
                </div>
            </div>,
            document.body
        );
    };

    // ==================== RENDER ====================
    if (loading) {
        return (
            <div className="frm-loading">
                <div className="frm-spinner" />
                <span>Caricamento...</span>
            </div>
        );
    }

    if (error) {
        return (
            <div className="frm-empty">
                <div className="frm-empty-icon" style={{ background: '#fee2e2', color: '#dc3545' }}><i className="ri-error-warning-line" /></div>
                <h5>Errore</h5>
                <p>{error}</p>
                <button className="frm-btn-primary" onClick={fetchData}><i className="ri-refresh-line" />Riprova</button>
            </div>
        );
    }

    // ==================== ADMIN VIEW ====================
    if (canManageTeamTraining) {
        // Detail view: training di un professionista
        if (adminView === 'trainings' && selectedProfessional) {
            const specialtyGradient = SPECIALTY_GRADIENTS[selectedProfessional.specialty] || DEFAULT_GRADIENT;

            return (
                <>
                    {/* Header */}
                    <div className="frm-detail-header">
                        <div className="frm-detail-header-left">
                            <button className="frm-btn-back" onClick={handleBackToProfessionals}>
                                <i className="ri-arrow-left-line" />
                            </button>
                            <div className="frm-detail-avatar" style={{ background: specialtyGradient }}>
                                {selectedProfessional.avatarPath
                                    ? <img src={selectedProfessional.avatarPath} alt="" />
                                    : `${selectedProfessional.firstName?.charAt(0) || ''}${selectedProfessional.lastName?.charAt(0) || ''}`
                                }
                            </div>
                            <div>
                                <div className="frm-detail-name">{selectedProfessional.firstName} {selectedProfessional.lastName}</div>
                                <div className="frm-detail-subtitle">{selectedProfessional.jobTitle || 'Professionista'} &middot; {selectedProfessional.department || '-'}</div>
                            </div>
                        </div>
                        <button className="frm-btn-primary" onClick={() => setShowNewTrainingModal(true)}>
                            <i className="ri-edit-line" />Scrivi Training
                        </button>
                    </div>

                    {/* Stats */}
                    <div className="frm-stat-grid">
                        <div className="frm-stat-card">
                            <div className="frm-stat-icon" style={{ background: 'rgba(111, 66, 193, 0.1)', color: '#6f42c1' }}><i className="ri-book-open-line" /></div>
                            <div>
                                <div className="frm-stat-value">{professionalTrainings.length}</div>
                                <div className="frm-stat-label">Training Totali</div>
                            </div>
                        </div>
                        <div className="frm-stat-card">
                            <div className="frm-stat-icon" style={{ background: 'rgba(255, 193, 7, 0.15)', color: '#d97706' }}><i className="ri-time-line" /></div>
                            <div>
                                <div className="frm-stat-value">{professionalTrainings.filter(t => !t.isAcknowledged && !t.isDraft).length}</div>
                                <div className="frm-stat-label">Da Confermare</div>
                            </div>
                        </div>
                        <div className="frm-stat-card">
                            <div className="frm-stat-icon" style={{ background: 'rgba(25, 135, 84, 0.1)', color: '#198754' }}><i className="ri-check-double-line" /></div>
                            <div>
                                <div className="frm-stat-value">{professionalTrainings.filter(t => t.isAcknowledged).length}</div>
                                <div className="frm-stat-label">Confermati</div>
                            </div>
                        </div>
                    </div>

                    {/* Training List */}
                    <div className="frm-card">
                        <div className="frm-card-header">
                            <h6 style={{ fontWeight: 600, margin: 0, display: 'flex', alignItems: 'center', gap: 8 }}>
                                <i className="ri-book-open-line" />Lista Training
                            </h6>
                        </div>
                        <div>
                            {professionalTrainings.length === 0
                                ? renderEmpty('ri-book-open-line', 'Nessun training ancora', `${selectedProfessional.firstName} non ha ancora ricevuto training. Scrivi il primo!`, <button className="frm-btn-primary" onClick={() => setShowNewTrainingModal(true)}><i className="ri-edit-line" />Scrivi il Primo Training</button>)
                                : professionalTrainings.map(t => renderTrainingRow(t, { isAdminReadOnly: true }))
                            }
                        </div>
                    </div>

                    {renderNewTrainingModal()}
                    {renderAckModal()}
                </>
            );
        }

        // Main admin view with tabs
        return (
            <div>
                {/* Header */}
                <div className="frm-page-header" data-tour="header">
                    <div>
                        <h4>Formazione</h4>
                        <p>{stats.unacknowledged > 0 ? `${stats.unacknowledged} training da confermare` : 'Gestione training e richieste di formazione'}</p>
                    </div>
                </div>

                {/* KPI Cards */}
                <div className="row g-3 mb-4" data-tour="stats-cards">
                    {[
                        { label: 'Training Ricevuti', value: stats.totalTrainings, icon: 'ri-book-open-line', color: '#3b82f6', badge: stats.unacknowledged > 0 ? stats.unacknowledged : null },
                        { label: 'Training Erogati', value: stats.totalGiven, icon: 'ri-presentation-line', color: '#22c55e', badge: stats.givenPending > 0 ? stats.givenPending : null },
                        { label: 'Richieste Ricevute', value: stats.receivedTotal, icon: 'ri-mail-download-line', color: '#0dcaf0', badge: stats.receivedPending > 0 ? stats.receivedPending : null },
                        { label: 'Richieste Inviate', value: requests.length, icon: 'ri-mail-send-line', color: '#f97316', badge: stats.pendingRequests > 0 ? stats.pendingRequests : null },
                    ].map((stat, idx) => (
                        <div key={idx} className="col-xl-3 col-sm-6">
                            <div className="frm-kpi-card">
                                <div className="d-flex justify-content-between align-items-center">
                                    <div>
                                        <div className="kpi-label">{stat.label}</div>
                                        <div className="d-flex align-items-center gap-2">
                                            <div className="kpi-value">{stat.value}</div>
                                            {stat.badge && <span className="frm-badge danger">{stat.badge}</span>}
                                        </div>
                                    </div>
                                    <div className="kpi-icon" style={{ background: `${stat.color}15`, color: stat.color }}>
                                        <i className={stat.icon} />
                                    </div>
                                </div>
                            </div>
                        </div>
                    ))}
                </div>

                <div data-tour="tabs-navigation">
                    {/* Main Tabs */}
                    <div className="formazione-tabs mb-4">
                        <button className={`formazione-tab${adminTab === 'myTrainings' ? ' active' : ''}`} onClick={() => setAdminTab('myTrainings')}>
                            <i className="ri-user-line" />I Miei Training
                            {stats.unacknowledged > 0 && <span className="formazione-tab-badge danger">{stats.unacknowledged}</span>}
                        </button>
                        <button className={`formazione-tab${adminTab === 'team' ? ' active' : ''}`} onClick={() => setAdminTab('team')}>
                            <i className="ri-team-line" />Gestione Team
                            <span className="formazione-tab-count">{professionals.length}</span>
                        </button>
                    </div>

                    {/* Tab: I Miei Training */}
                    {adminTab === 'myTrainings' && (
                        <div className="frm-card">
                            <div className="frm-card-header">
                                <div className="formazione-tabs formazione-subtabs">
                                    <button className={`formazione-tab${activeTab === 'trainings' ? ' active' : ''}`} onClick={() => setActiveTab('trainings')}>
                                        <i className="ri-book-open-line" /><span className="d-none d-sm-inline">Training </span>Ricevuti
                                        {stats.unacknowledged > 0 && <span className="formazione-tab-badge danger">{stats.unacknowledged}</span>}
                                    </button>
                                    <button className={`formazione-tab${activeTab === 'given' ? ' active' : ''}`} onClick={() => setActiveTab('given')}>
                                        <i className="ri-presentation-line" /><span className="d-none d-sm-inline">Training </span>Erogati
                                        {stats.givenPending > 0 && <span className="formazione-tab-badge warning">{stats.givenPending}</span>}
                                    </button>
                                    <button className={`formazione-tab${activeTab === 'received' ? ' active' : ''}`} onClick={() => setActiveTab('received')}>
                                        <i className="ri-mail-download-line" /><span className="d-none d-sm-inline">Richieste </span>Ricevute
                                        {stats.receivedPending > 0 && <span className="formazione-tab-badge info">{stats.receivedPending}</span>}
                                    </button>
                                </div>
                            </div>

                            <div className="frm-search-wrap">
                                <div className="frm-search-input">
                                    <i className="ri-search-line" />
                                    <input
                                        type="text" placeholder="Cerca training/richieste..."
                                        value={listSearch}
                                        onChange={(e) => { setTrainingsPage(1); setGivenTrainingsPage(1); setRequestsPage(1); setReceivedRequestsPage(1); setListSearch(e.target.value); }}
                                    />
                                </div>
                            </div>

                            <div>
                                {/* Training Ricevuti */}
                                {activeTab === 'trainings' && (
                                    <div data-tour="content-list">
                                        {filteredTrainings.length === 0
                                            ? renderEmpty('ri-book-open-line', 'Nessun training', 'Non hai ancora ricevuto training.')
                                            : filteredTrainings.slice((trainingsPage - 1) * ITEMS_PER_SECTION, trainingsPage * ITEMS_PER_SECTION).map(t => renderTrainingRow(t))
                                        }
                                        {renderPagination(filteredTrainings, trainingsPage, setTrainingsPage)}
                                    </div>
                                )}

                                {/* Training Erogati */}
                                {activeTab === 'given' && (
                                    <div>
                                        {filteredGivenTrainings.length === 0
                                            ? renderEmpty('ri-presentation-line', 'Nessun training erogato', 'Non hai ancora erogato training ad altri.')
                                            : filteredGivenTrainings.slice((givenTrainingsPage - 1) * ITEMS_PER_SECTION, givenTrainingsPage * ITEMS_PER_SECTION).map(t => renderTrainingRow(t, { showReviewer: false, showReviewee: true }))
                                        }
                                        {renderPagination(filteredGivenTrainings, givenTrainingsPage, setGivenTrainingsPage)}
                                    </div>
                                )}

                                {/* Richieste Ricevute */}
                                {activeTab === 'received' && (
                                    <div>
                                        {filteredReceivedRequests.length === 0
                                            ? renderEmpty('ri-mail-download-line', 'Nessuna richiesta ricevuta', 'Non hai ricevuto richieste di training.')
                                            : filteredReceivedRequests.slice((receivedRequestsPage - 1) * ITEMS_PER_SECTION, receivedRequestsPage * ITEMS_PER_SECTION).map(r => renderRequestRow(r))
                                        }
                                        {renderPagination(filteredReceivedRequests, receivedRequestsPage, setReceivedRequestsPage)}
                                    </div>
                                )}
                            </div>
                        </div>
                    )}

                    {/* Tab: Gestione Team */}
                    {adminTab === 'team' && (
                        <>
                            {/* Filters */}
                            <div className="frm-filter-bar">
                                <div style={{ position: 'relative', flex: 1, minWidth: 200 }}>
                                    <i className="ri-search-line" style={{ position: 'absolute', left: 12, top: '50%', transform: 'translateY(-50%)', color: 'var(--frm-text-light)' }} />
                                    <input
                                        type="text" placeholder="Cerca per nome o email..."
                                        value={adminFilters.search}
                                        onChange={(e) => handleAdminFilterChange('search', e.target.value)}
                                        style={{ paddingLeft: 36 }}
                                    />
                                </div>
                                <select
                                    value={adminFilters.specialty}
                                    onChange={(e) => handleAdminFilterChange('specialty', e.target.value)}
                                    disabled={isTeamLeader && !!teamLeaderSpecialtyFilterValue}
                                >
                                    <option value="">{isTeamLeader && teamLeaderSpecialtyGroup ? 'Solo la tua specialità' : 'Tutte le Specializzazioni'}</option>
                                    {allowedSpecialtyFilterOptions.map((opt) => (
                                        <option key={opt.value} value={opt.value}>{opt.label}</option>
                                    ))}
                                </select>
                                <button className="frm-btn-secondary" onClick={resetAdminFilters}>
                                    <i className="ri-refresh-line" />Reset
                                </button>
                            </div>

                            {/* Professional Cards */}
                            {filteredProfessionals.length === 0 ? (
                                <div className="frm-card">
                                    {renderEmpty('ri-user-search-line', 'Nessun professionista trovato', 'Prova a modificare i filtri di ricerca', <button className="frm-btn-primary" onClick={resetAdminFilters}><i className="ri-refresh-line" />Reset Filtri</button>)}
                                </div>
                            ) : (
                                <>
                                    <div className="frm-prof-grid">
                                        {paginatedProfessionals.map((member) => {
                                            const specColor = SPECIALTY_TEXT_COLORS[member.specialty] || '#64748b';
                                            return (
                                                <div key={member.id} className="frm-prof-card">
                                                    <div className="frm-prof-banner" style={{ background: SPECIALTY_GRADIENTS[member.specialty] || DEFAULT_GRADIENT }}>
                                                        <span className="frm-prof-role-badge" style={{ color: specColor }}>
                                                            {ROLE_LABELS[member.role] || 'N/D'}
                                                        </span>
                                                        <div className="frm-prof-avatar-wrap">
                                                            {member.avatarPath
                                                                ? <img className="frm-prof-avatar" src={member.avatarPath} alt="" />
                                                                : <div className="frm-prof-avatar-placeholder">{member.firstName?.[0]?.toUpperCase()}{member.lastName?.[0]?.toUpperCase()}</div>
                                                            }
                                                        </div>
                                                    </div>
                                                    <div className="frm-prof-body">
                                                        <div className="frm-prof-name">{member.firstName} {member.lastName}</div>
                                                        <div className="frm-prof-email">{member.email}</div>
                                                        {member.specialty && (
                                                            <span className="frm-prof-specialty" style={{ color: specColor, borderColor: `${specColor}30` }}>
                                                                {SPECIALTY_LABELS[member.specialty] || member.specialty}
                                                            </span>
                                                        )}
                                                    </div>
                                                    <div className="frm-prof-footer">
                                                        <button className="frm-btn-primary" onClick={() => handleSelectProfessional(member)}>
                                                            <i className="ri-book-open-line" />Vedi Training
                                                        </button>
                                                    </div>
                                                </div>
                                            );
                                        })}
                                    </div>

                                    {/* Pagination */}
                                    {totalPages > 1 && (
                                        <div className="form-pagination">
                                            <span className="form-pagination-info">Pagina {currentPage} di {totalPages} &middot; {filteredProfessionals.length} professionisti</span>
                                            <div className="form-pagination-buttons">
                                                <button className="form-page-btn" disabled={currentPage === 1} onClick={() => setCurrentPage(p => Math.max(1, p - 1))}>&laquo;</button>
                                                {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
                                                    let pageNum;
                                                    if (totalPages <= 5) pageNum = i + 1;
                                                    else if (currentPage <= 3) pageNum = i + 1;
                                                    else if (currentPage >= totalPages - 2) pageNum = totalPages - 4 + i;
                                                    else pageNum = currentPage - 2 + i;
                                                    return <button key={pageNum} className={`form-page-btn${currentPage === pageNum ? ' active' : ''}`} onClick={() => setCurrentPage(pageNum)}>{pageNum}</button>;
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

                {renderAckModal()}
                {renderRequestModal()}

                <SupportWidget
                    pageTitle="Formazione e Sviluppo"
                    pageDescription="Gestisci la tua crescita professionale, visualizza i training assegnati e richiedi supporto formativo."
                    pageIcon={({ size, color }) => <i className="ri-graduation-cap-line" style={{ fontSize: size, color }} />}
                    docsSection="formazione"
                    onStartTour={(audience) => {
                        setTourAudienceOverride(audience);
                        setMostraTour(true);
                    }}
                    brandName="Suite Clinica"
                    logoSrc="/suitemind.png"
                    accentColor="#6366F1"
                />

                <GuidedTour
                    steps={tourSteps}
                    isOpen={mostraTour}
                    onClose={() => setMostraTour(false)}
                    onComplete={() => { setMostraTour(false); console.log('Tour Formazione completato'); }}
                />
            </div>
        );
    }

    // ==================== USER VIEW ====================
    return (
        <>
            {/* Header */}
            <div className="frm-page-header" data-tour="header">
                <div>
                    <h4>La tua Formazione</h4>
                    <p>{stats.unacknowledged > 0 ? `${stats.unacknowledged} training da confermare` : 'Tutti i training confermati'}</p>
                </div>
                <button className="frm-btn-primary" onClick={() => setShowRequestModal(true)} disabled={recipientsLoading} data-tour="request-btn">
                    {recipientsLoading
                        ? <><span className="frm-spinner" style={{ width: 14, height: 14, borderWidth: 2 }} />Caricamento...</>
                        : <><i className="ri-add-circle-line" />Richiedi Training</>
                    }
                </button>
            </div>

            {/* KPI Cards */}
            <div className="row g-3 mb-4" data-tour="stats-cards">
                {[
                    { label: 'Training Ricevuti', value: stats.totalTrainings, icon: 'ri-book-open-line', color: '#3b82f6', badge: stats.unacknowledged > 0 ? `${stats.unacknowledged} da confermare` : null },
                    { label: 'Richieste Inviate', value: requests.length, icon: 'ri-file-list-3-line', color: '#0dcaf0', badge: stats.pendingRequests > 0 ? `${stats.pendingRequests} in attesa` : null },
                    { label: 'Messaggi non letti', value: stats.unreadMessages, icon: 'ri-message-3-line', color: stats.unreadMessages > 0 ? '#f97316' : '#22c55e' },
                    { label: 'Completati', value: stats.completedRequests, icon: 'ri-check-double-line', color: '#22c55e' },
                ].map((stat, idx) => (
                    <div key={idx} className="col-xl-3 col-sm-6">
                        <div className="frm-kpi-card">
                            <div className="d-flex justify-content-between align-items-center">
                                <div>
                                    <div className="kpi-label">{stat.label}</div>
                                    <div className="kpi-value">{stat.value}</div>
                                    {stat.badge && <div style={{ marginTop: 4 }}><span className="frm-badge warning" style={{ fontSize: 11 }}>{stat.badge}</span></div>}
                                </div>
                                <div className="kpi-icon" style={{ background: `${stat.color}15`, color: stat.color }}>
                                    <i className={stat.icon} />
                                </div>
                            </div>
                        </div>
                    </div>
                ))}
            </div>

            {/* Tab Navigation */}
            <div className="frm-card" data-tour="tabs-navigation">
                <div className="frm-card-header">
                    <div className="formazione-tabs formazione-subtabs">
                        <button className={`formazione-tab${activeTab === 'trainings' ? ' active' : ''}`} onClick={() => setActiveTab('trainings')}>
                            <i className="ri-book-open-line" />Training Ricevuti
                            {stats.unacknowledged > 0 && <span className="formazione-tab-badge danger">{stats.unacknowledged}</span>}
                        </button>
                        <button className={`formazione-tab${activeTab === 'requests' ? ' active' : ''}`} onClick={() => setActiveTab('requests')}>
                            <i className="ri-file-list-3-line" />Le Mie Richieste
                            {stats.pendingRequests > 0 && <span className="formazione-tab-badge warning">{stats.pendingRequests}</span>}
                        </button>
                    </div>
                </div>

                <div className="frm-search-wrap">
                    <div className="frm-search-input">
                        <i className="ri-search-line" />
                        <input type="text" placeholder="Cerca training/richieste..." value={listSearch} onChange={(e) => setListSearch(e.target.value)} />
                    </div>
                </div>

                <div data-tour="content-list">
                    {/* Training Ricevuti */}
                    {activeTab === 'trainings' && (
                        <div>
                            {filteredTrainings.length === 0
                                ? renderEmpty('ri-book-open-line', 'Nessun training', 'Non hai ancora ricevuto training.',
                                    recipients.length > 0 && <button className="frm-btn-primary" onClick={() => setShowRequestModal(true)}><i className="ri-add-circle-line" />Richiedi il tuo primo training</button>
                                )
                                : filteredTrainings.map(t => renderTrainingRow(t))
                            }
                        </div>
                    )}

                    {/* Richieste */}
                    {activeTab === 'requests' && (
                        <div>
                            {filteredRequests.length === 0
                                ? renderEmpty('ri-file-list-3-line', 'Nessuna richiesta', 'Non hai ancora inviato richieste di training.',
                                    recipients.length > 0 && <button className="frm-btn-primary" onClick={() => setShowRequestModal(true)}><i className="ri-add-circle-line" />Invia la tua prima richiesta</button>
                                )
                                : filteredRequests.map(r => renderRequestRow(r, { isSent: true }))
                            }
                        </div>
                    )}
                </div>
            </div>

            {renderAckModal()}
            {renderRequestModal()}

            <SupportWidget
                pageTitle="Formazione e Sviluppo"
                pageDescription="Gestisci la tua crescita professionale, visualizza i training assegnati e richiedi supporto formativo."
                pageIcon="ri-graduation-cap-line"
                docsSection="formazione"
                onStartTour={(audience) => {
                    setTourAudienceOverride(audience);
                    setMostraTour(true);
                }}
                brandName="Suite Clinica"
                logoSrc="/suitemind.png"
                accentColor="#6366F1"
            />

            <GuidedTour
                steps={tourSteps}
                isOpen={mostraTour}
                onClose={() => setMostraTour(false)}
                onComplete={() => { setMostraTour(false); console.log('Tour Formazione completato'); }}
            />
        </>
    );
}

export default Formazione;

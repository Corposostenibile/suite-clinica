import { useState, useEffect, useCallback, useMemo, useDeferredValue, useRef } from 'react';
import { useOutletContext, useNavigate, useSearchParams } from 'react-router-dom';
import taskService, { TASK_CATEGORIES, TASK_PRIORITIES } from '../../services/taskService';
import { ROLE_LABELS, SPECIALTY_LABELS } from '../../services/teamService';
import GuidedTour from '../../components/GuidedTour';
import SupportWidget from '../../components/SupportWidget';
import {
    FaTasks,
    FaClipboardList,
    FaStream,
    FaCheckCircle,
    FaArrowRight,
    FaFilter
} from 'react-icons/fa';
import './Task.css';

function Task() {
    const { user } = useOutletContext();
    const navigate = useNavigate();
    const [tasks, setTasks] = useState([]);
    const [stats, setStats] = useState({ by_category: {}, total_open: 0 });
    const [activeTab, setActiveTab] = useState('all');
    const [showCompleted, setShowCompleted] = useState(false);
    const [searchTerm, setSearchTerm] = useState('');
    const [currentPage, setCurrentPage] = useState(1);
    const [loading, setLoading] = useState(true);
    const [filterOptionsLoading, setFilterOptionsLoading] = useState(false);
    const [mostraTour, setMostraTour] = useState(false);
    const [searchParams] = useSearchParams();
    const [adminFilters, setAdminFilters] = useState({
        team_id: '',
        assignee_id: '',
        assignee_role: '',
        assignee_specialty: '',
    });
    const [adminFilterOptions, setAdminFilterOptions] = useState({
        teams: [],
        assignees: [],
        roles: [],
        specialties: [],
    });
    const [teamLeaderAssigneeId, setTeamLeaderAssigneeId] = useState('');
    const [detailTask, setDetailTask] = useState(null);

    const PAGE_SIZE = 15;
    const deferredSearchTerm = useDeferredValue(searchTerm.trim());
    const filterOptionsLoadedRef = useRef(false);
    const [pagination, setPagination] = useState({
        page: 1,
        per_page: PAGE_SIZE,
        total: 0,
        pages: 1,
    });
    const isGlobalTaskViewer = Boolean(
        user?.is_admin ||
        user?.role === 'admin' ||
        user?.specialty === 'cco'
    );
    const isTeamLeaderTaskViewer = Boolean(user?.role === 'team_leader' && !isGlobalTaskViewer);
    const showAssigneeColumn = isGlobalTaskViewer || isTeamLeaderTaskViewer;

    useEffect(() => {
        if (searchParams.get('startTour') === 'true') {
            setMostraTour(true);
        }
    }, [searchParams]);

    const totalPages = Math.max(1, pagination.pages || 1);
    const totalItems = pagination.total || 0;
    const currentPerPage = pagination.per_page || PAGE_SIZE;
    const pageStart = totalItems > 0 ? ((currentPage - 1) * currentPerPage) + 1 : 0;
    const pageEnd = totalItems > 0 ? Math.min(currentPage * currentPerPage, totalItems) : 0;

    const firstActionableIndex = tasks.findIndex(
        (t) => !t.completed && (t.client_id || (t.payload && (t.payload.client_id || t.payload.url)))
    );

    const tourSteps = useMemo(() => {
        const base = [
            {
                target: '[data-tour="header"]',
                title: 'Benvenuto al Sistema Task',
                content: isTeamLeaderTaskViewer
                    ? 'Questa è la tua console per monitorare e supportare il team sulle attività quotidiane.'
                    : 'Questa è la tua centrale operativa per gestire attività, scadenze e solleciti.',
                placement: 'bottom',
                icon: <FaTasks size={18} color="white" />,
                iconBg: 'linear-gradient(135deg, #6366F1, #8B5CF6)'
            },
            {
                target: '[data-tour="stats-cards"]',
                title: 'Dashboard Task',
                content: 'Le card mostrano il numero di attività aperte per categoria.',
                placement: 'bottom',
                icon: <FaStream size={18} color="white" />,
                iconBg: 'linear-gradient(135deg, #3B82F6, #60A5FA)'
            },
            {
                target: '[data-tour="task-table"]',
                title: 'La Tua Lista Attività',
                content: 'Ogni riga contiene tipo attività, cliente, scadenza e priorità.',
                placement: 'top',
                icon: <FaClipboardList size={18} color="white" />,
                iconBg: 'linear-gradient(135deg, #10B981, #34D399)'
            },
            {
                target: '[data-tour="task-checkbox"]',
                title: 'Completamento Task',
                content: 'Clicca la checkbox quando hai finito l’attività.',
                placement: 'right',
                icon: <FaCheckCircle size={18} color="white" />,
                iconBg: 'linear-gradient(135deg, #22c55e, #16a34a)'
            },
            {
                target: '[data-tour="task-action"]',
                title: 'Navigazione Intelligente',
                content: 'Il pulsante Vai ti porta direttamente nel punto operativo.',
                placement: 'left',
                icon: <FaArrowRight size={18} color="white" />,
                iconBg: 'linear-gradient(135deg, #8B5CF6, #D946EF)'
            },
            {
                target: '[data-tour="task-tabs"]',
                title: 'Filtri Comodi',
                content: 'Usa tab, ricerca e switch completate per restringere la vista.',
                placement: 'bottom',
                icon: <FaFilter size={18} color="white" />,
                iconBg: 'linear-gradient(135deg, #F59E0B, #FBBF24)'
            }
        ];

        if (isGlobalTaskViewer) {
            base.push({
                target: '[data-tour="task-admin-filters"]',
                title: 'Filtri Admin',
                content: 'Puoi filtrare per team, ruolo, specialità e assegnatario per analisi trasversali.',
                placement: 'bottom',
                icon: <FaFilter size={18} color="white" />,
                iconBg: 'linear-gradient(135deg, #0ea5e9, #0284c7)'
            });
        } else if (isTeamLeaderTaskViewer) {
            base.push({
                target: '[data-tour="task-team-filters"]',
                title: 'Filtro Team Leader',
                content: 'Seleziona un professionista del tuo team per fare focus su carico e avanzamento.',
                placement: 'bottom',
                icon: <FaFilter size={18} color="white" />,
                iconBg: 'linear-gradient(135deg, #0ea5e9, #0284c7)'
            });
        }

        return base;
    }, [isGlobalTaskViewer, isTeamLeaderTaskViewer]);

    const filteredTourSteps = tourSteps.filter(step => {
        if (step.target === '[data-tour="task-action"]' && firstActionableIndex === -1) return false;
        return true;
    });

    const fetchTasks = useCallback(async () => {
        setLoading(true);
        try {
            const params = {
                completed: showCompleted ? 'true' : 'false',
                paginate: 'true',
                page: currentPage,
                per_page: PAGE_SIZE,
                include_summary: 'true',
            };
            if (activeTab !== 'all') params.category = activeTab;
            if (deferredSearchTerm) params.q = deferredSearchTerm;
            if (isGlobalTaskViewer) {
                if (adminFilters.team_id) params.team_id = Number(adminFilters.team_id);
                if (adminFilters.assignee_id) params.assignee_id = Number(adminFilters.assignee_id);
                if (adminFilters.assignee_role) params.assignee_role = adminFilters.assignee_role;
                if (adminFilters.assignee_specialty) params.assignee_specialty = adminFilters.assignee_specialty;
            } else if (isTeamLeaderTaskViewer && teamLeaderAssigneeId) {
                params.assignee_id = Number(teamLeaderAssigneeId);
            }
            const data = await taskService.getAll(params);
            if (Array.isArray(data)) {
                setTasks(data);
                setPagination({
                    page: 1,
                    per_page: data.length || PAGE_SIZE,
                    total: data.length,
                    pages: 1,
                });
            } else {
                setTasks(data?.items || []);
                setPagination(data?.pagination || {
                    page: currentPage,
                    per_page: PAGE_SIZE,
                    total: 0,
                    pages: 1,
                });
            }
            if (data?.summary) {
                setStats(data.summary);
            }
        } catch (error) {
            console.error('Error fetching tasks:', error);
        } finally {
            setLoading(false);
        }
    }, [activeTab, showCompleted, currentPage, deferredSearchTerm, isGlobalTaskViewer, isTeamLeaderTaskViewer, adminFilters, teamLeaderAssigneeId]);

    const fetchFilterOptions = useCallback(async () => {
        if (!isGlobalTaskViewer && !isTeamLeaderTaskViewer) return;
        if (filterOptionsLoadedRef.current) return;
        setFilterOptionsLoading(true);
        try {
            const data = await taskService.getFilterOptions();
            setAdminFilterOptions({
                teams: data.teams || [],
                assignees: data.assignees || [],
                roles: data.roles || [],
                specialties: data.specialties || [],
            });
            filterOptionsLoadedRef.current = true;
        } catch (error) {
            console.error('Error fetching task filter options:', error);
        } finally {
            setFilterOptionsLoading(false);
        }
    }, [isGlobalTaskViewer, isTeamLeaderTaskViewer]);

    useEffect(() => {
        fetchTasks();
    }, [fetchTasks]);

    useEffect(() => {
        if (currentPage !== 1) {
            setCurrentPage(1);
        }
    }, [activeTab, showCompleted, deferredSearchTerm, adminFilters, teamLeaderAssigneeId]);

    useEffect(() => {
        if (currentPage > totalPages) setCurrentPage(totalPages);
    }, [currentPage, totalPages]);

    const toggleTask = async (taskId, currentStatus) => {
        setTasks(prev => prev.map(task => task.id === taskId ? { ...task, completed: !task.completed } : task));
        try {
            await taskService.toggleComplete(taskId, !currentStatus);
            if (!showCompleted) fetchTasks();
        } catch (error) {
            console.error('Error updating task:', error);
            fetchTasks();
        }
    };

    const handleTaskAction = (task) => {
        if (!task) return;
        const { category, payload, client_id } = task;
        const targetClientId = client_id || (payload ? payload.client_id : null);
        const targetUrl = payload ? payload.url : null;
        if (!targetClientId && !targetUrl) return;

        switch (category) {
            case 'check':
                if (targetClientId) navigate(`/clienti-dettaglio/${targetClientId}?tab=check`);
                break;
            case 'onboarding':
            case 'formazione':
            case 'sollecito':
            case 'reminder':
                if (targetClientId) navigate(`/clienti-dettaglio/${targetClientId}`);
                break;
            default:
                if (targetUrl) window.open(targetUrl, '_blank');
                else if (targetClientId) navigate(`/clienti-dettaglio/${targetClientId}`);
                break;
        }
    };

    const formatDate = (dateStr) => {
        if (!dateStr) return '';
        const date = new Date(dateStr);
        const today = new Date();
        const yesterday = new Date(today);
        yesterday.setDate(yesterday.getDate() - 1);
        if (date.toDateString() === today.toDateString()) return 'Oggi';
        if (date.toDateString() === yesterday.toDateString()) return 'Ieri';
        return date.toLocaleDateString('it-IT', { day: 'numeric', month: 'short' });
    };

    const getPriorityColor = (priority) => TASK_PRIORITIES[priority]?.color || '#6c757d';
    const getCategoryInfo = (catKey) => TASK_CATEGORIES[catKey] || { label: catKey, color: '#6c757d', bg: 'secondary' };
    const ensureFilterOptionsLoaded = useCallback(() => {
        if (filterOptionsLoadedRef.current || filterOptionsLoading) return;
        fetchFilterOptions();
    }, [fetchFilterOptions, filterOptionsLoading]);
    const roleOptions = useMemo(() => {
        return adminFilterOptions.roles || [];
    }, [adminFilterOptions.roles]);
    const specialtyOptions = useMemo(() => {
        return adminFilterOptions.specialties || [];
    }, [adminFilterOptions.specialties]);
    const filteredMemberOptions = useMemo(() => {
        if (!isGlobalTaskViewer) return [];
        return (adminFilterOptions.assignees || []).filter((m) => {
            if (adminFilters.assignee_role && m.role !== adminFilters.assignee_role) return false;
            if (adminFilters.assignee_specialty && m.specialty !== adminFilters.assignee_specialty) return false;
            if (adminFilters.team_id) {
                const teamIds = (m.teams || []).map((t) => String(t.id));
                if (!teamIds.includes(String(adminFilters.team_id))) return false;
            }
            return true;
        });
    }, [adminFilterOptions.assignees, adminFilters, isGlobalTaskViewer]);
    const teamLeaderMemberOptions = useMemo(() => {
        if (!isTeamLeaderTaskViewer) return [];
        return (adminFilterOptions.assignees || []).filter((m) => m.role !== 'admin');
    }, [adminFilterOptions.assignees, isTeamLeaderTaskViewer]);

    const completedCount = stats.total_completed || 0;
    const totalTaskCount = (stats.total_open || 0) + completedCount;
    const progressPct = totalTaskCount > 0 ? Math.round((completedCount / totalTaskCount) * 100) : 0;
    const showProgress = typeof stats.total_completed === 'number';

    const getCategoryBadgeStyle = (catKey) => {
        const colors = {
            onboarding: { bg: '#e0f7fa', color: '#00838f', border: '#b2ebf2' },
            check:      { bg: '#e8f5e9', color: '#2e7d32', border: '#c8e6c9' },
            reminder:   { bg: '#fff8e1', color: '#e65100', border: '#ffecb3' },
            formazione: { bg: '#ede7f6', color: '#5e35b1', border: '#d1c4e9' },
            sollecito:  { bg: '#fce4ec', color: '#c62828', border: '#f8bbd0' },
            generico:   { bg: '#f5f5f5', color: '#616161', border: '#e0e0e0' },
        };
        return colors[catKey] || colors.generico;
    };

    const getCategoryBarColor = (catKey) => {
        const map = {
            onboarding: '#17a2b8',
            check:      '#28a745',
            reminder:   '#dc8c14',
            formazione: '#6f42c1',
            sollecito:  '#dc3545',
            generico:   '#6c757d',
        };
        return map[catKey] || '#6c757d';
    };

    return (
        <div className="task-page">
            {/* --- HEADER --- */}
            <div className="task-header" data-tour="header">
                <div>
                    <h4>Le tue Task</h4>
                    <p>{stats.total_open} attivit&agrave; da completare</p>
                </div>
                <div className="task-header-actions">
                    <button className="task-refresh-btn" onClick={fetchTasks} title="Aggiorna">
                        <i className="ri-refresh-line"></i>
                    </button>
                    <div className="task-switch-container" data-tour="task-switch">
                        <input
                            className="form-check-input"
                            type="checkbox"
                            role="switch"
                            id="showCompleted"
                            checked={showCompleted}
                            onChange={(e) => setShowCompleted(e.target.checked)}
                        />
                        <label htmlFor="showCompleted">Mostra completate</label>
                    </div>
                </div>
            </div>

            {/* --- PROGRESS BAR --- */}
            {showProgress && (
                <div className="task-progress-bar-container">
                    <div className="task-progress-info">
                        <i className="ri-bar-chart-box-line"></i>
                        <span className="task-progress-label">Progresso</span>
                    </div>
                    <div className="task-progress-track">
                        <div className="task-progress-fill" style={{ width: `${progressPct}%` }}></div>
                    </div>
                    <span className="task-progress-pct">{progressPct}%</span>
                </div>
            )}

            {/* --- ADMIN FILTERS --- */}
            {isGlobalTaskViewer && (
                <div className="task-filter-card" data-tour="task-admin-filters">
                    <div className="task-filter-header">
                        <h6>Filtri Admin</h6>
                        <button
                            className="task-filter-reset-btn"
                            onClick={() => setAdminFilters({ team_id: '', assignee_id: '', assignee_role: '', assignee_specialty: '' })}
                        >
                            Reset filtri
                        </button>
                    </div>
                    {filterOptionsLoading && (
                        <div className="task-filter-hint" style={{ marginBottom: '10px' }}>
                            Caricamento filtri in corso...
                        </div>
                    )}
                    <div className="task-filter-grid">
                        <select
                            className="task-filter-select"
                            value={adminFilters.team_id}
                            onChange={(e) => setAdminFilters((prev) => ({ ...prev, team_id: e.target.value, assignee_id: '' }))}
                            onFocus={ensureFilterOptionsLoaded}
                            onClick={ensureFilterOptionsLoaded}
                            disabled={filterOptionsLoading}
                        >
                            <option value="">Tutti i team</option>
                            {(adminFilterOptions.teams || []).map((team) => (
                                <option key={team.id} value={team.id}>{team.name}</option>
                            ))}
                        </select>
                        <select
                            className="task-filter-select"
                            value={adminFilters.assignee_role}
                            onChange={(e) => setAdminFilters((prev) => ({ ...prev, assignee_role: e.target.value, assignee_id: '' }))}
                            onFocus={ensureFilterOptionsLoaded}
                            onClick={ensureFilterOptionsLoaded}
                            disabled={filterOptionsLoading}
                        >
                            <option value="">Tutti i ruoli</option>
                            {roleOptions.map((role) => (
                                <option key={role} value={role}>{ROLE_LABELS[role] || role}</option>
                            ))}
                        </select>
                        <select
                            className="task-filter-select"
                            value={adminFilters.assignee_specialty}
                            onChange={(e) => setAdminFilters((prev) => ({ ...prev, assignee_specialty: e.target.value, assignee_id: '' }))}
                            onFocus={ensureFilterOptionsLoaded}
                            onClick={ensureFilterOptionsLoaded}
                            disabled={filterOptionsLoading}
                        >
                            <option value="">Tutte le specialit&agrave;</option>
                            {specialtyOptions.map((spec) => (
                                <option key={spec} value={spec}>{SPECIALTY_LABELS[spec] || spec}</option>
                            ))}
                        </select>
                        <select
                            className="task-filter-select"
                            value={adminFilters.assignee_id}
                            onChange={(e) => setAdminFilters((prev) => ({ ...prev, assignee_id: e.target.value }))}
                            onFocus={ensureFilterOptionsLoaded}
                            onClick={ensureFilterOptionsLoaded}
                            disabled={filterOptionsLoading}
                        >
                            <option value="">Tutti gli assegnatari</option>
                            {filteredMemberOptions.map((m) => (
                                <option key={m.id} value={m.id}>
                                    {m.full_name || `${m.first_name || ''} ${m.last_name || ''}`.trim() || m.email || `#${m.id}`}
                                </option>
                            ))}
                        </select>
                    </div>
                </div>
            )}

            {/* --- TEAM LEADER FILTERS --- */}
            {isTeamLeaderTaskViewer && (
                <div className="task-filter-card" data-tour="task-team-filters">
                    <div className="task-filter-header">
                        <h6>Filtri Team</h6>
                        <button className="task-filter-reset-btn" onClick={() => setTeamLeaderAssigneeId('')}>
                            Reset filtro
                        </button>
                    </div>
                    {filterOptionsLoading && (
                        <div className="task-filter-hint" style={{ marginBottom: '10px' }}>
                            Caricamento filtri in corso...
                        </div>
                    )}
                    <div className="task-filter-grid" style={{ gridTemplateColumns: '1fr 1fr' }}>
                        <select
                            className="task-filter-select"
                            value={teamLeaderAssigneeId}
                            onChange={(e) => setTeamLeaderAssigneeId(e.target.value)}
                            onFocus={ensureFilterOptionsLoaded}
                            onClick={ensureFilterOptionsLoaded}
                            disabled={filterOptionsLoading}
                        >
                            <option value="">Tutto il team</option>
                            {teamLeaderMemberOptions.map((m) => (
                                <option key={m.id} value={m.id}>
                                    {m.full_name || `${m.first_name || ''} ${m.last_name || ''}`.trim() || m.email || `#${m.id}`}
                                </option>
                            ))}
                        </select>
                        <div className="d-flex align-items-center">
                            <span className="task-filter-hint">
                                Filtra i task per professionista del tuo team (fatte/da fare tramite toggle sopra).
                            </span>
                        </div>
                    </div>
                </div>
            )}

            {/* --- TABS (Segmented Control) --- */}
            <div className="task-tabs-container" data-tour="task-tabs">
                <div className="task-tabs">
                    <button
                        className={`task-tab${activeTab === 'all' ? ' active' : ''}`}
                        onClick={() => setActiveTab('all')}
                    >
                        Tutti
                        <span className="task-tab-count">{stats.total_open}</span>
                    </button>
                    {Object.entries(TASK_CATEGORIES).map(([key, cat]) => {
                        const count = stats.by_category?.[key] || 0;
                        if (count === 0 && activeTab !== key) return null;
                        return (
                            <button
                                key={key}
                                className={`task-tab${activeTab === key ? ' active' : ''}`}
                                onClick={() => setActiveTab(key)}
                            >
                                <i className={cat.icon}></i>
                                {cat.label}
                                <span className="task-tab-count">{count}</span>
                            </button>
                        );
                    })}
                </div>
            </div>

            {/* --- TASK LIST --- */}
            <div className="task-list-container" data-tour="task-table">
                {loading ? (
                    <div className="task-loading">
                        <div className="task-spinner"></div>
                        <p>Caricamento task...</p>
                    </div>
                ) : tasks.length === 0 ? (
                    <div className="task-empty">
                        <div className="task-empty-icon">
                            <i className="ri-checkbox-circle-line"></i>
                        </div>
                        <h5>
                            {showCompleted
                                ? 'Nessun task completato'
                                : searchTerm
                                    ? 'Nessun risultato'
                                    : 'Tutto fatto!'}
                        </h5>
                        <p>
                            {showCompleted
                                ? 'Non ci sono task completati con i filtri correnti.'
                                : searchTerm
                                    ? `Nessun task trovato per "${searchTerm}". Prova con un altro termine.`
                                    : 'Non hai attivit\u00e0 in sospeso. Ottimo lavoro!'}
                        </p>
                    </div>
                ) : (
                    <>
                        <div className="task-list">
                            {tasks.map((task, index) => {
                                const category = getCategoryInfo(task.category);
                                const priorityColor = getPriorityColor(task.priority);
                                const hasAction = task.client_id || (task.payload && (task.payload.client_id || task.payload.url));
                                const badgeStyle = getCategoryBadgeStyle(task.category);
                                const barColor = getCategoryBarColor(task.category);
                                const isOverdue = task.due_date && new Date(task.due_date) < new Date() && !task.completed;

                                return (
                                    <div
                                        key={task.id}
                                        className={`task-card-item${task.completed ? ' completed' : ''}`}
                                        style={{ '--card-bar-color': barColor }}
                                    >
                                        {/* Checkbox */}
                                        <div className="task-card-checkbox" data-tour={index === 0 ? 'task-checkbox' : undefined}>
                                            <div
                                                className={`task-custom-check${task.completed ? ' checked' : ''}`}
                                                onClick={() => toggleTask(task.id, task.completed)}
                                                role="checkbox"
                                                aria-checked={task.completed}
                                                tabIndex={0}
                                                onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); toggleTask(task.id, task.completed); }}}
                                            >
                                                {task.completed && <i className="ri-check-line"></i>}
                                            </div>
                                        </div>

                                        {/* Body */}
                                        <div className="task-card-body">
                                            <div className="task-card-title-row">
                                                <span className="task-card-title">{task.title}</span>
                                                <span
                                                    className="task-category-badge"
                                                    style={{ background: badgeStyle.bg, color: badgeStyle.color, borderColor: badgeStyle.border }}
                                                >
                                                    <i className={category.icon}></i>
                                                    {category.label}
                                                </span>
                                            </div>
                                            {task.description && (
                                                <span
                                                    className="task-card-details-link"
                                                    onClick={() => setDetailTask(task)}
                                                >
                                                    <i className="ri-file-text-line"></i>
                                                    Leggi Dettagli
                                                </span>
                                            )}
                                        </div>

                                        {/* Meta */}
                                        <div className="task-card-meta">
                                            {/* Client */}
                                            {task.client_name ? (
                                                <div className="task-card-client">
                                                    <div
                                                        className="task-card-client-avatar"
                                                        style={{ background: 'linear-gradient(135deg, #25B36A, #1a8a50)', color: 'white' }}
                                                    >
                                                        {task.client_name.substring(0, 2).toUpperCase()}
                                                    </div>
                                                    <span className="task-card-client-name">{task.client_name}</span>
                                                </div>
                                            ) : null}

                                            {/* Assignee */}
                                            {task.assignee_name && (
                                                <div className="task-card-assignee" title={task.assignee_name}>
                                                    {task.avatar_url || task.avatar_path ? (
                                                        <img
                                                            className="task-card-assignee-avatar"
                                                            src={task.avatar_url || task.avatar_path}
                                                            alt={task.assignee_name}
                                                        />
                                                    ) : (
                                                        <div className="task-card-assignee-avatar-fallback">
                                                            {task.assignee_name.split(' ').map(w => w[0]).join('').toUpperCase().slice(0, 2)}
                                                        </div>
                                                    )}
                                                    {showAssigneeColumn && (
                                                        <div className="task-card-assignee-info">
                                                            <span className="task-card-assignee-name">{task.assignee_name}</span>
                                                            <span className="task-card-assignee-role">
                                                                {[ROLE_LABELS[task.assignee_role] || task.assignee_role, SPECIALTY_LABELS[task.assignee_specialty] || task.assignee_specialty]
                                                                    .filter(Boolean)
                                                                    .join(' \u2022 ') || '\u2014'}
                                                            </span>
                                                        </div>
                                                    )}
                                                </div>
                                            )}

                                            {/* Action */}
                                            <div className="task-card-action" data-tour={index === firstActionableIndex ? 'task-action' : undefined}>
                                                {!task.completed && hasAction && (
                                                    <button
                                                        className="task-action-btn"
                                                        title="Vai"
                                                        onClick={() => handleTaskAction(task)}
                                                    >
                                                        <i className="ri-arrow-right-line"></i>
                                                    </button>
                                                )}
                                            </div>
                                        </div>
                                    </div>
                                );
                            })}
                        </div>

                        {/* --- PAGINATION --- */}
                        <div className="task-pagination-wrapper">
                            <span className="task-pagination-info">
                                Mostrando {pageStart}-{pageEnd} di {totalItems} task &middot; Pagina {currentPage}/{totalPages}
                            </span>
                            {totalPages > 1 && (
                                <div className="task-pagination-buttons">
                                    <button
                                        className="task-page-btn"
                                        disabled={currentPage === 1}
                                        onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
                                    >
                                        &laquo;
                                    </button>
                                    {Array.from({ length: totalPages }, (_, i) => i + 1)
                                        .filter((page) => page >= Math.max(1, currentPage - 2) && page <= Math.min(totalPages, currentPage + 2))
                                        .map((page) => (
                                            <button
                                                key={page}
                                                className={`task-page-btn${currentPage === page ? ' active' : ''}`}
                                                onClick={() => setCurrentPage(page)}
                                            >
                                                {page}
                                            </button>
                                        ))}
                                    <button
                                        className="task-page-btn"
                                        disabled={currentPage === totalPages}
                                        onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
                                    >
                                        &raquo;
                                    </button>
                                </div>
                            )}
                        </div>
                    </>
                )}
            </div>

            {/* --- DETAIL MODAL --- */}
            {detailTask && (
                <div className="task-modal-overlay" onClick={() => setDetailTask(null)}>
                    <div className="task-modal" onClick={(e) => e.stopPropagation()}>
                        <div className="task-modal-header">
                            <div className="task-modal-header-left">
                                <div
                                    className="task-modal-cat-dot"
                                    style={{ background: getCategoryBarColor(detailTask.category) }}
                                ></div>
                                <h5 className="task-modal-title">{detailTask.title}</h5>
                            </div>
                            <button className="task-modal-close" onClick={() => setDetailTask(null)}>
                                <i className="ri-close-line"></i>
                            </button>
                        </div>
                        <div className="task-modal-body">
                            <div className="task-modal-section">
                                <span className="task-modal-label">Descrizione</span>
                                <p className="task-modal-text">{detailTask.description}</p>
                            </div>
                            <div className="task-modal-grid">
                                <div className="task-modal-field">
                                    <span className="task-modal-label">Categoria</span>
                                    <span
                                        className="task-category-badge"
                                        style={{
                                            background: getCategoryBadgeStyle(detailTask.category).bg,
                                            color: getCategoryBadgeStyle(detailTask.category).color,
                                            borderColor: getCategoryBadgeStyle(detailTask.category).border,
                                        }}
                                    >
                                        <i className={getCategoryInfo(detailTask.category).icon}></i>
                                        {getCategoryInfo(detailTask.category).label}
                                    </span>
                                </div>
                                <div className="task-modal-field">
                                    <span className="task-modal-label">Stato</span>
                                    <span className={`task-modal-status ${detailTask.completed ? 'done' : 'open'}`}>
                                        {detailTask.completed ? 'Completata' : 'Da fare'}
                                    </span>
                                </div>
                                {detailTask.client_name && (
                                    <div className="task-modal-field">
                                        <span className="task-modal-label">Cliente</span>
                                        <div className="task-card-client">
                                            <div
                                                className="task-card-client-avatar"
                                                style={{ background: 'linear-gradient(135deg, #25B36A, #1a8a50)', color: 'white' }}
                                            >
                                                {detailTask.client_name.substring(0, 2).toUpperCase()}
                                            </div>
                                            <span className="task-card-client-name">{detailTask.client_name}</span>
                                        </div>
                                    </div>
                                )}
                                {detailTask.assignee_name && (
                                    <div className="task-modal-field">
                                        <span className="task-modal-label">Assegnatario</span>
                                        <div className="task-card-assignee">
                                            {detailTask.avatar_url || detailTask.avatar_path ? (
                                                <img
                                                    className="task-card-assignee-avatar"
                                                    src={detailTask.avatar_url || detailTask.avatar_path}
                                                    alt={detailTask.assignee_name}
                                                />
                                            ) : (
                                                <div className="task-card-assignee-avatar-fallback">
                                                    {detailTask.assignee_name.split(' ').map(w => w[0]).join('').toUpperCase().slice(0, 2)}
                                                </div>
                                            )}
                                            <div className="task-card-assignee-info">
                                                <span className="task-card-assignee-name">{detailTask.assignee_name}</span>
                                                <span className="task-card-assignee-role">
                                                    {[ROLE_LABELS[detailTask.assignee_role] || detailTask.assignee_role, SPECIALTY_LABELS[detailTask.assignee_specialty] || detailTask.assignee_specialty]
                                                        .filter(Boolean)
                                                        .join(' \u2022 ') || ''}
                                                </span>
                                            </div>
                                        </div>
                                    </div>
                                )}
                            </div>
                        </div>
                        <div className="task-modal-footer">
                            {!detailTask.completed && (detailTask.client_id || (detailTask.payload && (detailTask.payload.client_id || detailTask.payload.url))) && (
                                <button
                                    className="task-modal-go-btn"
                                    onClick={() => { handleTaskAction(detailTask); setDetailTask(null); }}
                                >
                                    Vai al cliente
                                    <i className="ri-arrow-right-line"></i>
                                </button>
                            )}
                            <button className="task-modal-close-btn" onClick={() => setDetailTask(null)}>
                                Chiudi
                            </button>
                        </div>
                    </div>
                </div>
            )}

            <SupportWidget
                pageTitle="Gestione Task"
                pageDescription="Organizza il tuo lavoro, gestisci i solleciti e monitora le scadenze dei pazienti."
                pageIcon={FaTasks}
                docsSection="task"
                onStartTour={() => setMostraTour(true)}
                brandName="Suite Clinica"
                logoSrc="/suitemind.png"
                accentColor="#85FF00"
            />

            <GuidedTour
                steps={filteredTourSteps}
                isOpen={mostraTour}
                onClose={() => setMostraTour(false)}
                onComplete={() => {
                    setMostraTour(false);
                    console.log('Tour Task completato');
                }}
            />
        </div>
    );
}

export default Task;

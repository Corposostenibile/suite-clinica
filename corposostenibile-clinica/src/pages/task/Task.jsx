import { useState, useEffect, useCallback, useMemo } from 'react';
import { useOutletContext, useNavigate, useSearchParams } from 'react-router-dom';
import taskService, { TASK_CATEGORIES, TASK_PRIORITIES } from '../../services/taskService';
import teamService, { ROLE_LABELS, SPECIALTY_LABELS } from '../../services/teamService';
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
        members: [],
    });

    const PAGE_SIZE = 15;
    const isGlobalTaskViewer = Boolean(
        user?.is_admin ||
        user?.role === 'admin' ||
        user?.specialty === 'cco'
    );

    useEffect(() => {
        if (searchParams.get('startTour') === 'true') {
            setMostraTour(true);
        }
    }, [searchParams]);

    const filteredTasks = useMemo(() => {
        const q = searchTerm.trim().toLowerCase();
        if (!q) return tasks;
        return tasks.filter((task) => {
            const title = (task.title || '').toLowerCase();
            const description = (task.description || '').toLowerCase();
            const client = (task.client_name || '').toLowerCase();
            const category = (task.category || '').toLowerCase();
            return (
                title.includes(q) ||
                description.includes(q) ||
                client.includes(q) ||
                category.includes(q)
            );
        });
    }, [tasks, searchTerm]);

    const totalPages = Math.max(1, Math.ceil(filteredTasks.length / PAGE_SIZE));
    const pageStart = (currentPage - 1) * PAGE_SIZE;
    const paginatedTasks = filteredTasks.slice(pageStart, pageStart + PAGE_SIZE);

    const firstActionableIndex = paginatedTasks.findIndex(
        (t) => !t.completed && (t.client_id || (t.payload && (t.payload.client_id || t.payload.url)))
    );

    const tourSteps = [
        {
            target: '[data-tour="header"]',
            title: 'Benvenuto al Sistema Task',
            content: 'Questa è la tua centrale operativa per gestire attività, scadenze e solleciti.',
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

    const filteredTourSteps = tourSteps.filter(step => {
        if (step.target === '[data-tour="task-action"]' && firstActionableIndex === -1) return false;
        return true;
    });

    const fetchStats = useCallback(async () => {
        try {
            const data = await taskService.getStats();
            setStats(data);
        } catch (error) {
            console.error('Error fetching stats:', error);
        }
    }, []);

    const fetchTasks = useCallback(async () => {
        setLoading(true);
        try {
            const params = {
                completed: showCompleted ? 'true' : 'false'
            };
            if (activeTab !== 'all') params.category = activeTab;
            if (isGlobalTaskViewer) {
                if (adminFilters.team_id) params.team_id = Number(adminFilters.team_id);
                if (adminFilters.assignee_id) params.assignee_id = Number(adminFilters.assignee_id);
                if (adminFilters.assignee_role) params.assignee_role = adminFilters.assignee_role;
                if (adminFilters.assignee_specialty) params.assignee_specialty = adminFilters.assignee_specialty;
            }
            const data = await taskService.getAll(params);
            setTasks(data);
        } catch (error) {
            console.error('Error fetching tasks:', error);
        } finally {
            setLoading(false);
        }
    }, [activeTab, showCompleted, isGlobalTaskViewer, adminFilters]);

    const fetchAdminFilterOptions = useCallback(async () => {
        if (!isGlobalTaskViewer) return;
        setFilterOptionsLoading(true);
        try {
            const [teamsRes, membersRes] = await Promise.all([
                teamService.getTeams({ per_page: 500, active: '1' }),
                teamService.getTeamMembers({ per_page: 5000, active: '1' }),
            ]);
            setAdminFilterOptions({
                teams: teamsRes.teams || [],
                members: membersRes.members || [],
            });
        } catch (error) {
            console.error('Error fetching task admin filter options:', error);
            setAdminFilterOptions({ teams: [], members: [] });
        } finally {
            setFilterOptionsLoading(false);
        }
    }, [isGlobalTaskViewer]);

    useEffect(() => {
        fetchStats();
    }, [fetchStats]);

    useEffect(() => {
        fetchTasks();
    }, [fetchTasks]);

    useEffect(() => {
        fetchAdminFilterOptions();
    }, [fetchAdminFilterOptions]);

    useEffect(() => {
        setCurrentPage(1);
    }, [activeTab, showCompleted, searchTerm, adminFilters]);

    useEffect(() => {
        if (currentPage > totalPages) setCurrentPage(totalPages);
    }, [currentPage, totalPages]);

    const toggleTask = async (taskId, currentStatus) => {
        setTasks(prev => prev.map(task => task.id === taskId ? { ...task, completed: !task.completed } : task));
        try {
            await taskService.toggleComplete(taskId, !currentStatus);
            fetchStats();
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
    const roleOptions = useMemo(() => {
        const roles = new Set((adminFilterOptions.members || []).map((m) => m.role).filter(Boolean));
        return Array.from(roles).sort();
    }, [adminFilterOptions.members]);
    const specialtyOptions = useMemo(() => {
        const specs = new Set((adminFilterOptions.members || []).map((m) => m.specialty).filter(Boolean));
        return Array.from(specs).sort();
    }, [adminFilterOptions.members]);
    const filteredMemberOptions = useMemo(() => {
        if (!isGlobalTaskViewer) return [];
        return (adminFilterOptions.members || []).filter((m) => {
            if (adminFilters.assignee_role && m.role !== adminFilters.assignee_role) return false;
            if (adminFilters.assignee_specialty && m.specialty !== adminFilters.assignee_specialty) return false;
            if (adminFilters.team_id) {
                const teamIds = (m.teams || []).map((t) => String(t.id));
                if (!teamIds.includes(String(adminFilters.team_id))) return false;
            }
            return true;
        });
    }, [adminFilterOptions.members, adminFilters, isGlobalTaskViewer]);

    return (
        <>
            <div className="d-flex flex-wrap align-items-center justify-content-between gap-3 mb-4" data-tour="header">
                <div>
                    <h4 className="mb-1">Le tue Task</h4>
                    <p className="text-muted mb-0">{stats.total_open} attività da completare</p>
                </div>
                <div className="d-flex gap-2">
                    <button className="btn btn-light" onClick={fetchTasks}>
                        <i className="ri-refresh-line"></i>
                    </button>
                    <div className="form-check form-switch d-flex align-items-center gap-2 m-0 border px-3 rounded bg-white" data-tour="task-switch">
                        <input
                            className="form-check-input m-0"
                            type="checkbox"
                            role="switch"
                            id="showCompleted"
                            checked={showCompleted}
                            onChange={(e) => setShowCompleted(e.target.checked)}
                        />
                        <label className="form-check-label text-muted small cursor-pointer" htmlFor="showCompleted">
                            Mostra completate
                        </label>
                    </div>
                </div>
            </div>

            <div className="card border-0 shadow-sm mb-3">
                <div className="card-body py-3">
                    <div className="position-relative">
                        <i className="ri-search-line position-absolute text-muted" style={{ left: '12px', top: '50%', transform: 'translateY(-50%)' }}></i>
                        <input
                            type="text"
                            className="form-control bg-light border-0"
                            placeholder="Cerca task per titolo, cliente, descrizione..."
                            value={searchTerm}
                            onChange={(e) => setSearchTerm(e.target.value)}
                            style={{ paddingLeft: '36px' }}
                        />
                    </div>
                </div>
            </div>

            {isGlobalTaskViewer && (
                <div className="card border-0 shadow-sm mb-3">
                    <div className="card-body py-3">
                        <div className="d-flex align-items-center justify-content-between mb-2">
                            <h6 className="mb-0">Filtri Admin</h6>
                            <button
                                className="btn btn-sm btn-outline-secondary"
                                onClick={() => setAdminFilters({ team_id: '', assignee_id: '', assignee_role: '', assignee_specialty: '' })}
                            >
                                Reset filtri
                            </button>
                        </div>
                        <div className="row g-2">
                            <div className="col-xl-3 col-md-6">
                                <select
                                    className="form-select bg-light border-0"
                                    value={adminFilters.team_id}
                                    onChange={(e) => setAdminFilters((prev) => ({ ...prev, team_id: e.target.value, assignee_id: '' }))}
                                    disabled={filterOptionsLoading}
                                >
                                    <option value="">Tutti i team</option>
                                    {(adminFilterOptions.teams || []).map((team) => (
                                        <option key={team.id} value={team.id}>{team.name}</option>
                                    ))}
                                </select>
                            </div>
                            <div className="col-xl-3 col-md-6">
                                <select
                                    className="form-select bg-light border-0"
                                    value={adminFilters.assignee_role}
                                    onChange={(e) => setAdminFilters((prev) => ({ ...prev, assignee_role: e.target.value, assignee_id: '' }))}
                                    disabled={filterOptionsLoading}
                                >
                                    <option value="">Tutti i ruoli</option>
                                    {roleOptions.map((role) => (
                                        <option key={role} value={role}>{ROLE_LABELS[role] || role}</option>
                                    ))}
                                </select>
                            </div>
                            <div className="col-xl-3 col-md-6">
                                <select
                                    className="form-select bg-light border-0"
                                    value={adminFilters.assignee_specialty}
                                    onChange={(e) => setAdminFilters((prev) => ({ ...prev, assignee_specialty: e.target.value, assignee_id: '' }))}
                                    disabled={filterOptionsLoading}
                                >
                                    <option value="">Tutte le specialità</option>
                                    {specialtyOptions.map((spec) => (
                                        <option key={spec} value={spec}>{SPECIALTY_LABELS[spec] || spec}</option>
                                    ))}
                                </select>
                            </div>
                            <div className="col-xl-3 col-md-6">
                                <select
                                    className="form-select bg-light border-0"
                                    value={adminFilters.assignee_id}
                                    onChange={(e) => setAdminFilters((prev) => ({ ...prev, assignee_id: e.target.value }))}
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
                    </div>
                </div>
            )}

            <div className="row g-3 mb-4" data-tour="stats-cards">
                {Object.entries(TASK_CATEGORIES).map(([key, cat]) => (
                    <div className="col-xl-2 col-md-4 col-6" key={key}>
                        <div
                            className={`card bg-${cat.bg} border-0 shadow-sm`}
                            onClick={() => setActiveTab(key)}
                            style={{
                                cursor: 'pointer',
                                opacity: activeTab === key ? 1 : 0.7,
                                transform: activeTab === key ? 'scale(1.02)' : 'scale(1)',
                                transition: 'all 0.2s',
                                color: '#fff'
                            }}
                        >
                            <div className="card-body py-3">
                                <div className="d-flex align-items-center justify-content-between">
                                    <div>
                                        <h3 className="text-white mb-0 fw-bold">
                                            {stats.by_category ? (stats.by_category[key] || 0) : 0}
                                        </h3>
                                        <span className="text-white opacity-75 small">{cat.label}</span>
                                    </div>
                                    <div className="bg-white bg-opacity-25 rounded-circle d-flex align-items-center justify-content-center" style={{ width: '40px', height: '40px' }}>
                                        <i className={`${cat.icon} text-white fs-5`}></i>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                ))}
            </div>

            <div className="card border-0 shadow-sm">
                <div className="card-header bg-white border-bottom-0 py-3" data-tour="task-tabs">
                    <ul className="nav nav-pills custom-pills">
                        <li className="nav-item">
                            <button className={`nav-link ${activeTab === 'all' ? 'active' : ''}`} onClick={() => setActiveTab('all')}>
                                <span className="me-2">Tutti</span>
                                <span className={`badge ${activeTab === 'all' ? 'bg-white text-primary' : 'bg-light text-muted'}`}>
                                    {stats.total_open}
                                </span>
                            </button>
                        </li>
                        {Object.entries(TASK_CATEGORIES).map(([key, cat]) => {
                            const count = stats.by_category?.[key] || 0;
                            if (count === 0 && activeTab !== key) return null;
                            return (
                                <li className="nav-item" key={key}>
                                    <button className={`nav-link ${activeTab === key ? 'active' : ''}`} onClick={() => setActiveTab(key)}>
                                        <i className={`${cat.icon} me-1`}></i>
                                        {cat.label}
                                        <span className={`badge ms-2 ${activeTab === key ? 'bg-white text-primary' : 'bg-light text-muted'}`}>
                                            {count}
                                        </span>
                                    </button>
                                </li>
                            );
                        })}
                    </ul>
                </div>

                <div className="card-body p-0" style={{ minHeight: '300px' }}>
                    {loading ? (
                        <div className="d-flex align-items-center justify-content-center h-100 py-5">
                            <div className="spinner-border text-primary" role="status">
                                <span className="visually-hidden">Loading...</span>
                            </div>
                        </div>
                    ) : filteredTasks.length === 0 ? (
                        <div className="text-center py-5">
                            <div className="mb-3">
                                <i className="ri-checkbox-circle-line text-success" style={{ fontSize: '64px', opacity: 0.5 }}></i>
                            </div>
                            <h5 className="text-muted">Nessun task da mostrare</h5>
                            <p className="text-muted small">Nessuna attività con i filtri correnti.</p>
                        </div>
                    ) : (
                        <div className="table-responsive">
                            <table className="table table-hover align-middle mb-0" data-tour="task-table">
                                <thead className="bg-light text-muted small uppercase">
                                    <tr>
                                        <th style={{ width: '50px' }}></th>
                                        <th>Attività</th>
                                        <th style={{ width: '150px' }}>Categoria</th>
                                        <th style={{ width: '150px' }}>Cliente</th>
                                        {isGlobalTaskViewer && <th style={{ width: '180px' }}>Assegnatario</th>}
                                        <th style={{ width: '120px' }}>Scadenza</th>
                                        <th style={{ width: '100px' }}>Priorità</th>
                                        <th style={{ width: '80px' }}></th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {paginatedTasks.map((task, index) => {
                                        const category = getCategoryInfo(task.category);
                                        const priorityColor = getPriorityColor(task.priority);
                                        const hasAction = task.client_id || (task.payload && (task.payload.client_id || task.payload.url));

                                        return (
                                            <tr key={task.id} className={task.completed ? 'bg-light opacity-75' : ''}>
                                                <td className="text-center" data-tour={index === 0 ? 'task-checkbox' : undefined}>
                                                    <div className="form-check d-flex justify-content-center">
                                                        <input
                                                            className="form-check-input"
                                                            type="checkbox"
                                                            checked={task.completed}
                                                            onChange={() => toggleTask(task.id, task.completed)}
                                                            style={{ cursor: 'pointer', transform: 'scale(1.2)' }}
                                                        />
                                                    </div>
                                                </td>
                                                <td>
                                                    <div className="d-flex flex-column">
                                                        <span className={`fw-medium ${task.completed ? 'text-decoration-line-through text-muted' : 'text-dark'}`}>
                                                            {task.title}
                                                        </span>
                                                        {task.description && (
                                                            <small className="text-muted">{task.description}</small>
                                                        )}
                                                    </div>
                                                </td>
                                                <td>
                                                    <span className={`badge bg-${category.bg} bg-opacity-10 text-${category.bg} border border-${category.bg} border-opacity-25`}>
                                                        <i className={`${category.icon} me-1`}></i>
                                                        {category.label}
                                                    </span>
                                                </td>
                                                <td>
                                                    {task.client_name ? (
                                                        <div className="d-flex align-items-center">
                                                            <div className="avatar-xs me-2 bg-light rounded-circle d-flex align-items-center justify-content-center text-primary fw-bold" style={{ width: '24px', height: '24px', fontSize: '10px' }}>
                                                                {task.client_name.substring(0, 2).toUpperCase()}
                                                            </div>
                                                            <span className="small fw-medium">{task.client_name}</span>
                                                        </div>
                                                    ) : (
                                                        <span className="text-muted small">-</span>
                                                    )}
                                                </td>
                                                {isGlobalTaskViewer && (
                                                    <td>
                                                        <div className="d-flex flex-column">
                                                            <span className="small fw-medium">{task.assignee_name || '-'}</span>
                                                            <small className="text-muted">
                                                                {[ROLE_LABELS[task.assignee_role] || task.assignee_role, SPECIALTY_LABELS[task.assignee_specialty] || task.assignee_specialty]
                                                                    .filter(Boolean)
                                                                    .join(' • ') || '—'}
                                                            </small>
                                                        </div>
                                                    </td>
                                                )}
                                                <td>
                                                    <small className={`${task.due_date && new Date(task.due_date) < new Date() && !task.completed ? 'text-danger fw-bold' : 'text-muted'}`}>
                                                        {formatDate(task.due_date)}
                                                    </small>
                                                </td>
                                                <td>
                                                    <div className="d-flex align-items-center gap-1">
                                                        <div style={{ width: '8px', height: '8px', borderRadius: '50%', backgroundColor: priorityColor }}></div>
                                                        <small style={{ color: priorityColor, fontWeight: 500 }}>
                                                            {TASK_PRIORITIES[task.priority]?.label || task.priority}
                                                        </small>
                                                    </div>
                                                </td>
                                                <td className="text-end" data-tour={index === firstActionableIndex ? 'task-action' : undefined}>
                                                    {!task.completed && hasAction && (
                                                        <button className="btn btn-icon btn-sm btn-ghost-primary" title="Vai" onClick={() => handleTaskAction(task)}>
                                                            <i className="ri-arrow-right-line"></i>
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

                {filteredTasks.length > 0 && (
                    <div className="card-footer bg-white py-3 border-top-0">
                        <div className="d-flex justify-content-between align-items-center text-muted small">
                            <span>Visualizzi {filteredTasks.length} task</span>
                            <span>
                                Pagina {currentPage}/{totalPages}
                            </span>
                        </div>
                        {filteredTasks.length > PAGE_SIZE && (
                            <div className="d-flex justify-content-end mt-3">
                                <nav>
                                    <ul className="pagination pagination-sm mb-0">
                                        <li className={`page-item ${currentPage === 1 ? 'disabled' : ''}`}>
                                            <button className="page-link" onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}>
                                                &laquo;
                                            </button>
                                        </li>
                                        {Array.from({ length: totalPages }, (_, i) => i + 1)
                                            .filter((page) => page >= Math.max(1, currentPage - 2) && page <= Math.min(totalPages, currentPage + 2))
                                            .map((page) => (
                                                <li key={page} className={`page-item ${currentPage === page ? 'active' : ''}`}>
                                                    <button className="page-link" onClick={() => setCurrentPage(page)}>
                                                        {page}
                                                    </button>
                                                </li>
                                            ))}
                                        <li className={`page-item ${currentPage === totalPages ? 'disabled' : ''}`}>
                                            <button className="page-link" onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}>
                                                &raquo;
                                            </button>
                                        </li>
                                    </ul>
                                </nav>
                            </div>
                        )}
                    </div>
                )}
            </div>

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
        </>
    );
}

export default Task;

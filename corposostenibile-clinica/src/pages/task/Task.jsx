import { useState, useEffect, useCallback } from 'react';
import { useOutletContext, useNavigate } from 'react-router-dom';
import taskService, { TASK_CATEGORIES, TASK_PRIORITIES } from '../../services/taskService';
import GuidedTour from '../../components/GuidedTour';
import SupportWidget from '../../components/SupportWidget';
import { 
    FaTasks, 
    FaClipboardCheck, 
    FaClipboardList,
    FaBell, 
    FaGraduationCap, 
    FaExclamationTriangle, 
    FaStickyNote, 
    FaStream, 
    FaCheckCircle, 
    FaArrowRight, 
    FaFilter,
    FaSync
} from 'react-icons/fa';

function Task() {
    const { user } = useOutletContext();
    const navigate = useNavigate();
    const [tasks, setTasks] = useState([]);
    const [stats, setStats] = useState({ by_category: {}, total_open: 0 });
    const [activeTab, setActiveTab] = useState('all');
    const [showCompleted, setShowCompleted] = useState(false);
    const [loading, setLoading] = useState(true);
    const [mostraTour, setMostraTour] = useState(false);

    const tourSteps = [
        {
            target: '[data-tour="header"]',
            title: 'Benvenuto al Sistema Task',
            content: 'Questa è la tua centrale operativa per gestire attività, scadenze e solleciti. È progettata per aiutarti a organizzare il lavoro in modo efficiente.',
            placement: 'bottom',
            icon: <FaTasks size={18} color="white" />,
            iconBg: 'linear-gradient(135deg, #6366F1, #8B5CF6)'
        },
        {
            target: '[data-tour="stats-cards"]',
            title: 'Dashboard Task',
            content: 'Ogni card rappresenta una categoria di attività aperte: \n\n• Onboarding (Blu): Nuovi clienti\n• Check (Verde): Controlli periodici\n• Reminder (Arancione): Scadenze imminenti\n• Formazione (Viola): Apprendimento\n• Solleciti (Rosso): Clienti non rispondenti\n• Generico (Grigio): Task manuali dai colleghi',
            placement: 'bottom',
            icon: <FaStream size={18} color="white" />,
            iconBg: 'linear-gradient(135deg, #3B82F6, #60A5FA)'
        },
        {
            target: '[data-tour="task-table"]',
            title: 'La Tua Lista Attività',
            content: 'Qui trovi tutte le attività da svolgere. Ogni riga contiene i dettagli necessari: il tipo di attività, il cliente collegato, la scadenza e la priorità.',
            placement: 'top',
            icon: <FaClipboardList size={18} color="white" />,
            iconBg: 'linear-gradient(135deg, #10B981, #34D399)'
        },
        {
            target: '[data-tour="task-checkbox"]',
            title: 'Completamento Task',
            content: 'Quando finisci un\'attività, clicca sulla checkbox. Il task verrà segnato come completato e sparirà dalla vista per mantenere la lista pulita.',
            placement: 'right',
            icon: <FaCheckCircle size={18} color="white" />,
            iconBg: 'linear-gradient(135deg, #22c55e, #16a34a)'
        },
        {
            target: '[data-tour="task-action"]',
            title: 'Navigazione Intelligente',
            content: 'Il pulsante "Vai" ti porta automaticamente dove devi operare: nella scheda cliente, nella sezione check o direttamente ai materiali formativi.',
            placement: 'left',
            icon: <FaArrowRight size={18} color="white" />,
            iconBg: 'linear-gradient(135deg, #8B5CF6, #D946EF)'
        },
        {
            target: '[data-tour="task-tabs"]',
            title: 'Filtri Comodi',
            content: 'Usa i tab per visualizzare solo una categoria specifica. Puoi anche ricaricare i dati o mostrare i task già completati per consultare lo storico.',
            placement: 'bottom',
            icon: <FaFilter size={18} color="white" />,
            iconBg: 'linear-gradient(135deg, #F59E0B, #FBBF24)'
        }
    ];

    const fetchStats = useCallback(async () => {
        try {
            const data = await taskService.getStats();
            setStats(data);
        } catch (error) {
            console.error("Error fetching stats:", error);
        }
    }, []);

    const fetchTasks = useCallback(async () => {
        setLoading(true);
        try {
            const params = {
                completed: showCompleted ? 'true' : 'false'
            };
            if (activeTab !== 'all') {
                params.category = activeTab;
            }
            
            const data = await taskService.getAll(params);
            setTasks(data);
        } catch (error) {
            console.error("Error fetching tasks:", error);
        } finally {
            setLoading(false);
        }
    }, [activeTab, showCompleted]);

    useEffect(() => {
        fetchStats();
    }, [fetchStats]);

    useEffect(() => {
        fetchTasks();
    }, [fetchTasks]);

    const toggleTask = async (taskId, currentStatus) => {
        // Optimistic update
        setTasks(prev => prev.map(task =>
            task.id === taskId ? { ...task, completed: !task.completed } : task
        ));

        try {
            await taskService.toggleComplete(taskId, !currentStatus);
            // Refresh stats to ensure sync
            fetchStats();
            // If we are filtering by completion, the task might disappear, so maybe refresh list?
            if (!showCompleted) {
                 fetchTasks();
            }
        } catch (error) {
            console.error("Error updating task:", error);
            // Revert on error
            fetchTasks();
        }
    };

    const handleTaskAction = (task) => {
        if (!task || !task.payload) return;

        const { category, payload } = task;

        switch (category) {
            case 'check':
                if (payload.client_id) {
                    // Navigate to client details, tab 'check'
                    navigate(`/clienti-dettaglio/${payload.client_id}?tab=check`);
                }
                break;
            case 'onboarding':
            case 'formazione': // Forse formazione porta al training, ma per ora cliente è sicuro
            case 'sollecito':
                if (payload.client_id) {
                     navigate(`/clienti-dettaglio/${payload.client_id}`);
                }
                break;
            case 'reminder':
                 if (payload.client_id) {
                     navigate(`/clienti-dettaglio/${payload.client_id}`);
                }
                break;
            default:
                // If there's a generic link in payload
                if (payload.url) {
                    window.open(payload.url, '_blank');
                } else if (payload.client_id) {
                     navigate(`/clienti-dettaglio/${payload.client_id}`);
                }
                break;
        }
    };

    const formatDate = (dateStr) => {
        if (!dateStr) return '';
        const date = new Date(dateStr);
        const today = new Date();
        const yesterday = new Date(today);
        yesterday.setDate(yesterday.getDate() - 1);

        if (date.toDateString() === today.toDateString()) {
            return 'Oggi';
        } else if (date.toDateString() === yesterday.toDateString()) {
            return 'Ieri';
        } else {
            return date.toLocaleDateString('it-IT', { day: 'numeric', month: 'short' });
        }
    };

    const getPriorityColor = (priority) => {
        return TASK_PRIORITIES[priority]?.color || '#6c757d';
    };

    // Helper per ottenere label categoria anche se non in TASK_CATEGORIES (fallback)
    const getCategoryInfo = (catKey) => {
        return TASK_CATEGORIES[catKey] || { label: catKey, color: '#6c757d', bg: 'secondary' };
    };

    return (
        <>
            {/* Page Header */}
            <div className="d-flex flex-wrap align-items-center justify-content-between gap-3 mb-4" data-tour="header">
                <div>
                    <h4 className="mb-1">Le tue Task</h4>
                    <p className="text-muted mb-0">
                        {stats.total_open} attività da completare
                    </p>
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
                            style={{ cursor: 'pointer' }}
                        />
                        <label className="form-check-label text-muted small cursor-pointer" htmlFor="showCompleted" style={{ cursor: 'pointer' }}>
                            Mostra completate
                        </label>
                    </div>
                </div>
            </div>

            {/* Stats Cards */}
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
                                    <div
                                        className="bg-white bg-opacity-25 rounded-circle d-flex align-items-center justify-content-center"
                                        style={{ width: '40px', height: '40px' }}
                                    >
                                        <i className={`${cat.icon} text-white fs-5`}></i>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                ))}
            </div>

            {/* Task List */}
            <div className="card border-0 shadow-sm">
                {/* Tabs */}
                <div className="card-header bg-white border-bottom-0 py-3" data-tour="task-tabs">
                    <ul className="nav nav-pills custom-pills">
                        <li className="nav-item">
                             <button
                                className={`nav-link ${activeTab === 'all' ? 'active' : ''}`}
                                onClick={() => setActiveTab('all')}
                            >
                                <span className="me-2">Tutti</span>
                                <span className={`badge ${activeTab === 'all' ? 'bg-white text-primary' : 'bg-light text-muted'}`}>
                                    {stats.total_open}
                                </span>
                            </button>
                        </li>
                        {Object.entries(TASK_CATEGORIES).map(([key, cat]) => {
                             const count = stats.by_category?.[key] || 0;
                             if (count === 0 && activeTab !== key) return null; // Hide empty tabs if not active

                             return (
                                <li className="nav-item" key={key}>
                                    <button
                                        className={`nav-link ${activeTab === key ? 'active' : ''}`}
                                        onClick={() => setActiveTab(key)}
                                    >
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

                {/* Task Items */}
                <div className="card-body p-0" style={{ minHeight: '300px' }}>
                    {loading ? (
                        <div className="d-flex align-items-center justify-content-center h-100 py-5">
                            <div className="spinner-border text-primary" role="status">
                                <span className="visually-hidden">Loading...</span>
                            </div>
                        </div>
                    ) : tasks.length === 0 ? (
                        <div className="text-center py-5">
                            <div className="mb-3">
                                <i className="ri-checkbox-circle-line text-success" style={{ fontSize: '64px', opacity: 0.5 }}></i>
                            </div>
                            <h5 className="text-muted">Nessun task da mostrare</h5>
                            <p className="text-muted small">Tutte le attività in questa categoria sono state completate!</p>
                        </div>
                    ) : (
                        <div className="table-responsive">
                            <table className="table table-hover align-middle mb-0">
                                <thead className="bg-light text-muted small uppercase" data-tour="task-table">
                                    <tr>
                                        <th style={{ width: '50px' }}></th>
                                        <th>Attività</th>
                                        <th style={{ width: '150px' }}>Categoria</th>
                                        <th style={{ width: '150px' }}>Cliente</th>
                                        <th style={{ width: '120px' }}>Scadenza</th>
                                        <th style={{ width: '100px' }}>Priorità</th>
                                        <th style={{ width: '80px' }}></th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {tasks.map((task, index) => {
                                        const category = getCategoryInfo(task.category);
                                        const priorityColor = getPriorityColor(task.priority);
                                        const hasAction = task.payload && (task.payload.client_id || task.payload.url);
                                        
                                        return (
                                            <tr key={task.id} className={task.completed ? 'bg-light opacity-75' : ''}>
                                                <td className="text-center" data-tour={index === 0 ? "task-checkbox" : undefined}>
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
                                                            <small className="text-muted">
                                                                {task.description}
                                                            </small>
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
                                                            <div className="avatar-xs me-2 bg-light rounded-circle d-flex align-items-center justify-content-center text-primary fw-bold" style={{width:'24px', height:'24px', fontSize:'10px'}}>
                                                                {task.client_name.substring(0,2).toUpperCase()}
                                                            </div>
                                                            <span className="small fw-medium">{task.client_name}</span>
                                                        </div>
                                                    ) : (
                                                        <span className="text-muted small">-</span>
                                                    )}
                                                </td>
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
                                                <td className="text-end" data-tour={index === 0 ? "task-action" : undefined}>
                                                    {!task.completed && hasAction && (
                                                        <button 
                                                            className="btn btn-icon btn-sm btn-ghost-primary" 
                                                            title="Vai"
                                                            onClick={() => handleTaskAction(task)}
                                                        >
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
                
                {/* Footer / Pagination */}
                {tasks.length > 0 && (
                    <div className="card-footer bg-white py-3 border-top-0">
                        <div className="d-flex justify-content-between align-items-center text-muted small">
                            <span>Visualizzi {tasks.length} task</span>
                            <span>Ordina per: <span className="fw-medium text-dark cursor-pointer">Priorità</span></span>
                        </div>
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
                steps={tourSteps}
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

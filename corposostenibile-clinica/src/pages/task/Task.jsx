import { useState, useEffect, useCallback } from 'react';
import { useOutletContext } from 'react-router-dom';
import api from '../../services/api';

// Categorie task (Mappate su Enum Backend)
const TASK_CATEGORIES = {
    all: { label: 'Tutti', icon: 'ri-list-check', color: '#6c757d', bg: 'secondary' },
    onboarding: { label: 'Onboarding', icon: 'ri-user-add-line', color: '#17a2b8', bg: 'info' },
    check: { label: 'Check', icon: 'ri-file-list-3-line', color: '#28a745', bg: 'success' },
    reminder: { label: 'Reminder', icon: 'ri-alarm-warning-line', color: '#dc8c14', bg: 'warning' },
    formazione: { label: 'Formazione', icon: 'ri-book-open-line', color: '#6f42c1', bg: 'primary' },
    sollecito: { label: 'Solleciti', icon: 'ri-time-line', color: '#dc3545', bg: 'danger' }, // Added Solleciti
};

function Task() {
    const { user } = useOutletContext();
    const [tasks, setTasks] = useState([]);
    const [stats, setStats] = useState({ by_category: {}, total_open: 0 });
    const [activeTab, setActiveTab] = useState('all');
    const [showCompleted, setShowCompleted] = useState(false);
    const [loading, setLoading] = useState(true);

    const fetchStats = useCallback(async () => {
        try {
            const response = await api.get('/tasks/stats');
            setStats(response.data);
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
            
            const response = await api.get('/tasks/', { params });
            setTasks(response.data);
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
            await api.put(`/tasks/${taskId}`, {
                completed: !currentStatus
            });
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
        switch (priority) {
            case 'high': return '#dc3545';
            case 'medium': return '#ffc107';
            case 'low': return '#28a745';
            case 'urgent': return '#dc3545'; // Added urgent
            default: return '#6c757d';
        }
    };

    // Helper per ottenere label categoria anche se non in TASK_CATEGORIES (fallback)
    const getCategoryInfo = (catKey) => {
        return TASK_CATEGORIES[catKey] || { label: catKey, color: '#6c757d', bg: 'secondary' };
    };

    return (
        <>
            {/* Page Header */}
            <div className="d-flex flex-wrap align-items-center justify-content-between gap-3 mb-4">
                <div>
                    <h4 className="mb-1">Le tue Task</h4>
                    <p className="text-muted mb-0">
                        {stats.total_open} attività da completare
                    </p>
                </div>
                <div className="form-check form-switch">
                    <input
                        className="form-check-input"
                        type="checkbox"
                        id="showCompleted"
                        checked={showCompleted}
                        onChange={(e) => setShowCompleted(e.target.checked)}
                    />
                    <label className="form-check-label text-muted" htmlFor="showCompleted">
                        Mostra completate
                    </label>
                </div>
            </div>

            {/* Stats Cards */}
            <div className="row g-3 mb-4">
                {Object.entries(TASK_CATEGORIES).filter(([key]) => key !== 'all').map(([key, cat]) => (
                    <div className="col-xl-2 col-md-4 col-6" key={key}>
                        <div
                            className={`card bg-${cat.bg} border-0 shadow-sm`}
                            onClick={() => setActiveTab(key)}
                            style={{ cursor: 'pointer', opacity: activeTab === key ? 1 : 0.85, transition: 'all 0.2s' }}
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
            <div className="card">
                {/* Tabs */}
                <div className="card-header bg-white border-bottom">
                    <ul className="nav nav-tabs card-header-tabs">
                        {Object.keys(TASK_CATEGORIES).map((key) => {
                            const cat = TASK_CATEGORIES[key];
                            const count = key === 'all' ? stats.total_open : (stats.by_category?.[key] || 0);
                            
                            return (
                                <li className="nav-item" key={key}>
                                    <button
                                        className={`nav-link ${activeTab === key ? 'active' : ''}`}
                                        onClick={() => setActiveTab(key)}
                                    >
                                        <i className={`${cat.icon} me-1`}></i>
                                        {cat.label}
                                        {count > 0 && (
                                            <span className={`badge ${activeTab === key ? 'bg-primary' : 'bg-secondary'} ms-2`}>
                                                {count}
                                            </span>
                                        )}
                                    </button>
                                </li>
                            );
                        })}
                    </ul>
                </div>

                {/* Task Items */}
                <div className="card-body p-0" style={{ maxHeight: '600px', overflowY: 'auto' }}>
                    {loading ? (
                        <div className="text-center py-5">
                            <div className="spinner-border text-primary" role="status">
                                <span className="visually-hidden">Loading...</span>
                            </div>
                        </div>
                    ) : tasks.length === 0 ? (
                        <div className="text-center py-5 text-muted">
                            <i className="ri-checkbox-circle-line text-success" style={{ fontSize: '64px' }}></i>
                            <h5 className="mt-3 mb-1">Tutto fatto!</h5>
                            <p className="text-muted">Non hai task da completare in questa categoria.</p>
                        </div>
                    ) : (
                        <table className="table table-hover mb-0">
                            <tbody>
                                {tasks.map(task => {
                                    const category = getCategoryInfo(task.category);
                                    const userName = user?.first_name || 'Professionista';
                                    
                                    // Use format client name if available, else standard message logic
                                    // Backend sends client_name
                                    
                                    return (
                                        <tr
                                            key={task.id}
                                            className={task.completed ? 'table-light' : ''}
                                            style={{ transition: 'all 0.2s' }}
                                        >
                                            {/* Checkbox */}
                                            <td style={{ width: '50px', verticalAlign: 'middle' }}>
                                                <div className="form-check">
                                                    <input
                                                        className="form-check-input"
                                                        type="checkbox"
                                                        checked={task.completed}
                                                        onChange={() => toggleTask(task.id, task.completed)}
                                                        style={{
                                                            width: '20px',
                                                            height: '20px',
                                                            cursor: 'pointer'
                                                        }}
                                                    />
                                                </div>
                                            </td>

                                            {/* Priority indicator */}
                                            <td style={{ width: '6px', padding: 0 }}>
                                                <div
                                                    style={{
                                                        width: '4px',
                                                        height: '100%',
                                                        minHeight: '60px',
                                                        background: task.completed ? '#dee2e6' : getPriorityColor(task.priority),
                                                        borderRadius: '2px'
                                                    }}
                                                />
                                            </td>

                                            {/* Content */}
                                            <td className="py-3">
                                                <div className="d-flex align-items-start justify-content-between">
                                                    <div className="flex-grow-1">
                                                        <div className="d-flex align-items-center gap-2 mb-1">
                                                            <span
                                                                className="badge"
                                                                style={{
                                                                    background: task.completed ? '#e9ecef' : `${category.color}15`,
                                                                    color: task.completed ? '#6c757d' : category.color,
                                                                    fontWeight: 500
                                                                }}
                                                            >
                                                                {category.label}
                                                            </span>
                                                            <span className="text-muted small">
                                                                {formatDate(task.created_at)}
                                                                {task.due_date && ` • Scadenza: ${formatDate(task.due_date)}`}
                                                            </span>
                                                        </div>
                                                        <p className={`mb-2 ${task.completed ? 'text-muted text-decoration-line-through' : ''}`}>
                                                            {task.description || task.title}
                                                        </p>
                                                        {task.client_name && (
                                                            <div className="d-flex align-items-center gap-2">
                                                                <span className="badge bg-light text-dark border">
                                                                    <i className="ri-user-line me-1"></i>
                                                                    {task.client_name}
                                                                </span>
                                                            </div>
                                                        )}
                                                    </div>
                                                    {/* Action */}
                                                    <div className="ms-3">
                                                        {!task.completed && (
                                                            <button className="btn btn-sm btn-outline-primary" onClick={() => {/* Navigate details? */}}>
                                                                Vai <i className="ri-arrow-right-line ms-1"></i>
                                                            </button>
                                                        )}
                                                        {task.completed && (
                                                            <span className="badge bg-success-subtle text-success">
                                                                <i className="ri-check-line me-1"></i>
                                                                Completata
                                                            </span>
                                                        )}
                                                    </div>
                                                </div>
                                            </td>
                                        </tr>
                                    );
                                })}
                            </tbody>
                        </table>
                    )}
                </div>

                {/* Footer */}
                {tasks.length > 0 && (
                    <div className="card-footer bg-white text-muted small">
                        <div className="d-flex align-items-center justify-content-between">
                            <span>
                                {tasks.filter(t => !t.completed).length} da completare
                            </span>
                            <div className="d-flex align-items-center gap-3">
                                <span className="d-flex align-items-center gap-1">
                                    <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: '#dc3545' }}></span>
                                    Alta
                                </span>
                                <span className="d-flex align-items-center gap-1">
                                    <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: '#ffc107' }}></span>
                                    Media
                                </span>
                                <span className="d-flex align-items-center gap-1">
                                    <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: '#28a745' }}></span>
                                    Bassa
                                </span>
                            </div>
                        </div>
                    </div>
                )}
            </div>
        </>
    );
}

export default Task;

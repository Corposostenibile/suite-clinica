import { useState } from 'react';
import { useOutletContext } from 'react-router-dom';

// Categorie task
const TASK_CATEGORIES = {
    all: { label: 'Tutti', icon: 'ri-list-check', color: '#6c757d', bg: 'secondary' },
    onboarding: { label: 'Onboarding', icon: 'ri-user-add-line', color: '#17a2b8', bg: 'info' },
    check: { label: 'Check', icon: 'ri-file-list-3-line', color: '#28a745', bg: 'success' },
    reminder: { label: 'Reminder', icon: 'ri-alarm-warning-line', color: '#dc8c14', bg: 'warning' },
    formazione: { label: 'Formazione', icon: 'ri-book-open-line', color: '#6f42c1', bg: 'primary' },
};

// Nomi clienti per mock data
const clientNames = [
    'Marco Rossi', 'Laura Bianchi', 'Giuseppe Verdi', 'Anna Ferrari', 'Paolo Esposito',
    'Francesca Romano', 'Luigi Conte', 'Maria Greco', 'Alessandro Marino', 'Chiara Costa',
    'Davide Ricci', 'Elena Fontana', 'Fabio Lombardi', 'Giulia Moretti', 'Luca Barbieri',
    'Sara Galli', 'Andrea Conti', 'Valentina Serra', 'Matteo Fabbri', 'Silvia Martini'
];

const coordinatorNames = [
    'Dr. Mario Bianchi', 'Dr.ssa Elena Supervisore', 'Dr. Francesco Coordinatore',
    'Dr.ssa Lucia Responsabile', 'Dr. Antonio Manager'
];

// Genera mock data
const generateMockTasks = () => {
    const tasks = [];
    let id = 1;

    // Onboarding tasks (12)
    for (let i = 0; i < 12; i++) {
        const daysAgo = Math.floor(Math.random() * 5);
        const date = new Date();
        date.setDate(date.getDate() - daysAgo);
        tasks.push({
            id: id++,
            category: 'onboarding',
            clientName: clientNames[i % clientNames.length],
            message: 'ti è stato assegnato un nuovo cliente. Mandagli un messaggio di benvenuto!',
            completed: i > 8,
            date: date.toISOString().split('T')[0],
            time: `${String(8 + Math.floor(Math.random() * 10)).padStart(2, '0')}:${String(Math.floor(Math.random() * 60)).padStart(2, '0')}`,
            priority: i < 3 ? 'high' : i < 7 ? 'medium' : 'low'
        });
    }

    // Check tasks (15)
    for (let i = 0; i < 15; i++) {
        const daysAgo = Math.floor(Math.random() * 7);
        const date = new Date();
        date.setDate(date.getDate() - daysAgo);
        tasks.push({
            id: id++,
            category: 'check',
            clientName: clientNames[(i + 5) % clientNames.length],
            message: 'hai ricevuto un nuovo check dal cliente. Leggilo!',
            completed: i > 10,
            date: date.toISOString().split('T')[0],
            time: `${String(7 + Math.floor(Math.random() * 12)).padStart(2, '0')}:${String(Math.floor(Math.random() * 60)).padStart(2, '0')}`,
            priority: i < 4 ? 'high' : i < 9 ? 'medium' : 'low'
        });
    }

    // Reminder tasks (18)
    for (let i = 0; i < 18; i++) {
        const daysAgo = Math.floor(Math.random() * 4);
        const date = new Date();
        date.setDate(date.getDate() - daysAgo);
        tasks.push({
            id: id++,
            category: 'reminder',
            clientName: clientNames[(i + 10) % clientNames.length],
            message: 'ieri il cliente non ha compilato il suo check settimanale, sollecitalo!',
            completed: i > 12,
            date: date.toISOString().split('T')[0],
            time: '07:00',
            priority: i < 5 ? 'high' : i < 10 ? 'medium' : 'low'
        });
    }

    // Formazione tasks (10)
    for (let i = 0; i < 10; i++) {
        const daysAgo = Math.floor(Math.random() * 10);
        const date = new Date();
        date.setDate(date.getDate() - daysAgo);
        tasks.push({
            id: id++,
            category: 'formazione',
            clientName: coordinatorNames[i % coordinatorNames.length],
            message: 'hai ricevuto un nuovo training. Leggilo!',
            completed: i > 6,
            date: date.toISOString().split('T')[0],
            time: `${String(9 + Math.floor(Math.random() * 8)).padStart(2, '0')}:${String(Math.floor(Math.random() * 60)).padStart(2, '0')}`,
            priority: i < 2 ? 'high' : i < 5 ? 'medium' : 'low'
        });
    }

    // Ordina per data (più recenti prima) e poi per priorità
    return tasks.sort((a, b) => {
        if (a.completed !== b.completed) return a.completed ? 1 : -1;
        const dateCompare = new Date(b.date) - new Date(a.date);
        if (dateCompare !== 0) return dateCompare;
        const priorityOrder = { high: 0, medium: 1, low: 2 };
        return priorityOrder[a.priority] - priorityOrder[b.priority];
    });
};

const mockTasks = generateMockTasks();

function Task() {
    const { user } = useOutletContext();
    const [tasks, setTasks] = useState(mockTasks);
    const [activeTab, setActiveTab] = useState('all');
    const [showCompleted, setShowCompleted] = useState(false);

    const toggleTask = (taskId) => {
        setTasks(prev => prev.map(task =>
            task.id === taskId ? { ...task, completed: !task.completed } : task
        ));
    };

    const filteredTasks = tasks.filter(task => {
        const categoryMatch = activeTab === 'all' || task.category === activeTab;
        const completedMatch = showCompleted || !task.completed;
        return categoryMatch && completedMatch;
    });

    const getTaskCounts = () => {
        const counts = { all: 0 };
        Object.keys(TASK_CATEGORIES).forEach(cat => {
            if (cat !== 'all') {
                counts[cat] = tasks.filter(t => t.category === cat && !t.completed).length;
                counts.all += counts[cat];
            }
        });
        return counts;
    };

    const taskCounts = getTaskCounts();

    const formatDate = (dateStr) => {
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
            default: return '#6c757d';
        }
    };

    return (
        <>
            {/* Page Header */}
            <div className="d-flex flex-wrap align-items-center justify-content-between gap-3 mb-4">
                <div>
                    <h4 className="mb-1">Le tue Task</h4>
                    <p className="text-muted mb-0">
                        {taskCounts.all} attività da completare
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
                    <div className="col-xl-3 col-sm-6" key={key}>
                        <div
                            className={`card bg-${cat.bg} border-0 shadow-sm`}
                            onClick={() => setActiveTab(key)}
                            style={{ cursor: 'pointer', opacity: activeTab === key ? 1 : 0.85, transition: 'all 0.2s' }}
                        >
                            <div className="card-body py-3">
                                <div className="d-flex align-items-center justify-content-between">
                                    <div>
                                        <h3 className="text-white mb-0 fw-bold">{taskCounts[key]}</h3>
                                        <span className="text-white opacity-75 small">{cat.label}</span>
                                    </div>
                                    <div
                                        className="bg-white bg-opacity-25 rounded-circle d-flex align-items-center justify-content-center"
                                        style={{ width: '48px', height: '48px' }}
                                    >
                                        <i className={`${cat.icon} text-white fs-4`}></i>
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
                        {Object.entries(TASK_CATEGORIES).map(([key, cat]) => (
                            <li className="nav-item" key={key}>
                                <button
                                    className={`nav-link ${activeTab === key ? 'active' : ''}`}
                                    onClick={() => setActiveTab(key)}
                                >
                                    <i className={`${cat.icon} me-1`}></i>
                                    {cat.label}
                                    {taskCounts[key] > 0 && (
                                        <span className={`badge ${activeTab === key ? 'bg-primary' : 'bg-secondary'} ms-2`}>
                                            {key === 'all' ? taskCounts.all : taskCounts[key]}
                                        </span>
                                    )}
                                </button>
                            </li>
                        ))}
                    </ul>
                </div>

                {/* Task Items */}
                <div className="card-body p-0" style={{ maxHeight: '600px', overflowY: 'auto' }}>
                    {filteredTasks.length === 0 ? (
                        <div className="text-center py-5 text-muted">
                            <i className="ri-checkbox-circle-line text-success" style={{ fontSize: '64px' }}></i>
                            <h5 className="mt-3 mb-1">Tutto fatto!</h5>
                            <p className="text-muted">Non hai task da completare in questa categoria.</p>
                        </div>
                    ) : (
                        <table className="table table-hover mb-0">
                            <tbody>
                                {filteredTasks.map(task => {
                                    const category = TASK_CATEGORIES[task.category];
                                    const userName = user?.first_name || 'Professionista';
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
                                                        onChange={() => toggleTask(task.id)}
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
                                                                {formatDate(task.date)} • {task.time}
                                                            </span>
                                                        </div>
                                                        <p className={`mb-2 ${task.completed ? 'text-muted text-decoration-line-through' : ''}`}>
                                                            Ciao <strong>{userName}</strong>, {task.message}
                                                        </p>
                                                        <div className="d-flex align-items-center gap-2">
                                                            <span className="badge bg-light text-dark border">
                                                                <i className="ri-user-line me-1"></i>
                                                                {task.clientName}
                                                            </span>
                                                        </div>
                                                    </div>
                                                    {/* Action */}
                                                    <div className="ms-3">
                                                        {!task.completed && (
                                                            <button className="btn btn-sm btn-outline-primary">
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
                {filteredTasks.length > 0 && (
                    <div className="card-footer bg-white text-muted small">
                        <div className="d-flex align-items-center justify-content-between">
                            <span>
                                {filteredTasks.filter(t => !t.completed).length} da completare
                                {showCompleted && ` • ${filteredTasks.filter(t => t.completed).length} completate`}
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

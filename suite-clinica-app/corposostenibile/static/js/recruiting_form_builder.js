/**
 * ═══════════════════════════════════════════════════════════════════════════
 * RECRUITING FORM BUILDER - Perfect ATS with Expected Answers
 * ═══════════════════════════════════════════════════════════════════════════
 *
 * Features:
 * - Drag & Drop questions reordering
 * - Expected answer configuration per tipo
 * - Match type selection per MULTISELECT
 * - Real-time weight calculation
 * - Smart UI based on question type
 */

// ═══════════════════════════════════════════════════════════════════════
// GLOBAL STATE
// ═══════════════════════════════════════════════════════════════════════
let questions = window.FormBuilder?.questions || [];
let editingQuestionId = null;
const OFFER_ID = window.OFFER_ID || null;

// ═══════════════════════════════════════════════════════════════════════
// QUESTION TYPE LABELS
// ═══════════════════════════════════════════════════════════════════════
const QUESTION_TYPE_LABELS = {
    'short_text': 'Testo breve',
    'long_text': 'Testo lungo',
    'select': 'Scelta singola',
    'multiselect': 'Scelta multipla',
    'number': 'Numero',
    'date': 'Data',
    'file': 'File',
    'email': 'Email',
    'phone': 'Telefono',
    'url': 'URL',
    'yesno': 'Sì/No'
};

const MATCH_TYPE_LABELS = {
    'exact_all': {
        label: 'Esattamente TUTTE',
        description: '100 punti solo se seleziona ESATTAMENTE queste opzioni (niente di più, niente di meno)',
        icon: 'ri-checkbox-multiple-line'
    },
    'contains_all': {
        label: 'Deve contenere TUTTE',
        description: '100 punti se contiene TUTTE le opzioni selezionate (tollerate opzioni extra)',
        icon: 'ri-checkbox-circle-line'
    },
    'exact_any': {
        label: 'Almeno UNA',
        description: '100 punti se seleziona ALMENO UNA delle opzioni',
        icon: 'ri-check-line'
    },
    'partial': {
        label: 'Score parziale',
        description: 'Score proporzionale (es: 2/3 corrette = 66%) con penalità per opzioni extra',
        icon: 'ri-percent-line'
    }
};

// ═══════════════════════════════════════════════════════════════════════
// INIT
// ═══════════════════════════════════════════════════════════════════════
document.addEventListener('DOMContentLoaded', function() {
    console.log('[Form Builder] Initializing...');
    loadQuestions();
    initDragAndDrop();
    updateTotalWeight();
});

// ═══════════════════════════════════════════════════════════════════════
// LOAD QUESTIONS from server
// ═══════════════════════════════════════════════════════════════════════
async function loadQuestions() {
    if (!OFFER_ID) {
        console.error('[Form Builder] OFFER_ID not set');
        return;
    }

    try {
        const response = await fetch(`/recruiting/offers/${OFFER_ID}/questions-data`);
        const data = await response.json();
        questions = data.questions || [];
        renderQuestions();
        updateTotalWeight();
    } catch (error) {
        console.error('[Form Builder] Error loading questions:', error);
        showToast('Errore caricamento domande', 'error');
    }
}

// ═══════════════════════════════════════════════════════════════════════
// RENDER ALL QUESTIONS
// ═══════════════════════════════════════════════════════════════════════
function renderQuestions() {
    const container = document.getElementById('questionsContainer');
    if (!container) return;

    if (questions.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <i class="ri-survey-line"></i>
                <h4>Nessuna domanda</h4>
                <p class="mb-3">Inizia aggiungendo la tua prima domanda al form</p>
                <button class="btn btn-primary btn-lg" onclick="addNewQuestion()">
                    <i class="ri-add-line me-2"></i>
                    Aggiungi Prima Domanda
                </button>
            </div>
        `;
        return;
    }

    // Sort by order
    questions.sort((a, b) => (a.order || 0) - (b.order || 0));

    container.innerHTML = questions.map(q => renderQuestionCard(q)).join('');

    // Re-init drag and drop
    initDragAndDrop();
}

// ═══════════════════════════════════════════════════════════════════════
// RENDER SINGLE QUESTION CARD
// ═══════════════════════════════════════════════════════════════════════
function renderQuestionCard(question) {
    const typeLabel = QUESTION_TYPE_LABELS[question.question_type] || question.question_type;

    return `
        <div class="question-card ${editingQuestionId === question.id ? 'editing' : ''}"
             data-question-id="${question.id}"
             draggable="true">

            <div class="drag-handle">
                <i class="ri-draggable"></i>
            </div>

            <div class="question-controls">
                <button class="btn btn-sm btn-outline-primary" onclick="editQuestion(${question.id})">
                    <i class="ri-edit-line"></i> Modifica
                </button>
                <button class="btn btn-sm btn-outline-danger" onclick="deleteQuestion(${question.id})">
                    <i class="ri-delete-bin-line"></i>
                </button>
            </div>

            <div class="mb-3">
                <div class="d-flex align-items-start gap-3">
                    <div class="flex-grow-1">
                        <h6 class="fw-bold mb-2">
                            ${question.question_text}
                            ${question.is_required ? '<span class="required-indicator ms-2"><i class="ri-star-fill"></i> Obbligatoria</span>' : ''}
                        </h6>
                        <p class="text-muted small mb-2">
                            <i class="ri-questionnaire-line me-1"></i>
                            <strong>Tipo:</strong> ${typeLabel}
                        </p>
                        ${question.help_text ? `<p class="text-muted small mb-0"><i class="ri-information-line me-1"></i>${question.help_text}</p>` : ''}
                    </div>
                    <div class="weight-badge">
                        <i class="ri-percent-line"></i>
                        ${question.weight || 0}%
                    </div>
                </div>
            </div>

            ${renderQuestionPreview(question)}
            ${renderExpectedAnswerPreview(question)}
        </div>
    `;
}

// ═══════════════════════════════════════════════════════════════════════
// RENDER QUESTION PREVIEW (form field simulated)
// ═══════════════════════════════════════════════════════════════════════
function renderQuestionPreview(question) {
    const type = question.question_type;

    let preview = '';

    if (type === 'select') {
        const options = question.options || [];
        preview = `
            <select class="form-select" disabled>
                <option>Seleziona...</option>
                ${options.map(opt => `<option>${opt}</option>`).join('')}
            </select>
        `;
    } else if (type === 'multiselect') {
        const options = question.options || [];
        preview = `
            <div class="border rounded p-3 bg-light">
                ${options.map(opt => `
                    <div class="form-check">
                        <input class="form-check-input" type="checkbox" disabled>
                        <label class="form-check-label">${opt}</label>
                    </div>
                `).join('')}
            </div>
        `;
    } else if (type === 'yesno') {
        preview = `
            <div class="btn-group w-100" role="group">
                <button type="button" class="btn btn-outline-success" disabled>Sì</button>
                <button type="button" class="btn btn-outline-danger" disabled>No</button>
            </div>
        `;
    } else if (type === 'short_text') {
        preview = `<input type="text" class="form-control" placeholder="${question.placeholder || ''}" disabled>`;
    } else if (type === 'long_text') {
        preview = `<textarea class="form-control" rows="3" placeholder="${question.placeholder || ''}" disabled></textarea>`;
    } else if (type === 'number') {
        preview = `<input type="number" class="form-control" placeholder="0" disabled>`;
    } else if (type === 'date') {
        preview = `<input type="date" class="form-control" disabled>`;
    } else if (type === 'email') {
        preview = `<input type="email" class="form-control" placeholder="email@example.com" disabled>`;
    } else if (type === 'phone') {
        preview = `<input type="tel" class="form-control" placeholder="+39 333 1234567" disabled>`;
    } else if (type === 'file') {
        preview = `<input type="file" class="form-control" disabled>`;
    } else {
        preview = `<div class="text-muted small">Campo tipo: ${type}</div>`;
    }

    return `<div class="mb-3">${preview}</div>`;
}

// ═══════════════════════════════════════════════════════════════════════
// RENDER EXPECTED ANSWER PREVIEW (NUOVO!)
// ═══════════════════════════════════════════════════════════════════════
function renderExpectedAnswerPreview(question) {
    const type = question.question_type;

    // Solo per tipi che hanno expected answer
    if (!['select', 'multiselect', 'yesno', 'number'].includes(type)) {
        return '';
    }

    let content = '';

    if (type === 'select' && question.expected_answer) {
        content = `
            <p class="mb-0 small">
                <i class="ri-check-line text-success me-1"></i>
                <strong>Risposta corretta:</strong> ${question.expected_answer}
            </p>
        `;
    } else if (type === 'multiselect' && question.expected_options && question.expected_options.length > 0) {
        const matchType = question.expected_match_type || 'partial';
        const matchInfo = MATCH_TYPE_LABELS[matchType];

        content = `
            <p class="mb-2 small">
                <i class="ri-check-line text-success me-1"></i>
                <strong>Risposte attese:</strong> ${question.expected_options.join(', ')}
            </p>
            <p class="mb-0 small">
                <i class="${matchInfo.icon} text-primary me-1"></i>
                <strong>Modalità:</strong> ${matchInfo.label}
            </p>
        `;
    } else if (type === 'yesno' && question.expected_answer) {
        content = `
            <p class="mb-0 small">
                <i class="ri-check-line text-success me-1"></i>
                <strong>Risposta corretta:</strong> ${question.expected_answer}
            </p>
        `;
    } else if (type === 'number' && (question.expected_min !== null || question.expected_max !== null)) {
        if (question.expected_min !== null && question.expected_max !== null) {
            content = `
                <p class="mb-0 small">
                    <i class="ri-check-line text-success me-1"></i>
                    <strong>Range atteso:</strong> ${question.expected_min} - ${question.expected_max}
                </p>
            `;
        } else if (question.expected_min !== null) {
            content = `
                <p class="mb-0 small">
                    <i class="ri-check-line text-success me-1"></i>
                    <strong>Minimo atteso:</strong> ≥ ${question.expected_min}
                </p>
            `;
        } else if (question.expected_max !== null) {
            content = `
                <p class="mb-0 small">
                    <i class="ri-check-line text-success me-1"></i>
                    <strong>Massimo atteso:</strong> ≤ ${question.expected_max}
                </p>
            `;
        }
    }

    if (!content) return '';

    return `
        <div class="expected-section">
            <div class="expected-section-title">
                <i class="ri-target-line"></i>
                Scoring ATS
            </div>
            ${content}
        </div>
    `;
}

// ═══════════════════════════════════════════════════════════════════════
// UPDATE TOTAL WEIGHT
// ═══════════════════════════════════════════════════════════════════════
function updateTotalWeight() {
    const total = questions.reduce((sum, q) => sum + (parseFloat(q.weight) || 0), 0);
    const displayEl = document.getElementById('totalWeight');
    const statusEl = document.getElementById('weightStatus');

    if (!displayEl) return;

    displayEl.textContent = `${total.toFixed(1)}%`;
    displayEl.dataset.weight = total;

    // Update color class
    displayEl.classList.remove('perfect', 'warning', 'error');

    if (Math.abs(total - 100) < 0.1) {
        displayEl.classList.add('perfect');
        if (statusEl) {
            statusEl.innerHTML = '<p class="mb-0"><i class="ri-check-line me-1"></i><strong>Perfetto!</strong> ✅</p>';
        }
    } else if (total < 100) {
        displayEl.classList.add('warning');
        if (statusEl) {
            statusEl.innerHTML = `<p class="mb-0"><i class="ri-alert-line me-1"></i>Mancano <strong>${(100 - total).toFixed(1)}%</strong> ⚠️</p>`;
        }
    } else {
        displayEl.classList.add('error');
        if (statusEl) {
            statusEl.innerHTML = `<p class="mb-0"><i class="ri-close-line me-1"></i>Eccesso <strong>${(total - 100).toFixed(1)}%</strong> ❌</p>`;
        }
    }
}

// ═══════════════════════════════════════════════════════════════════════
// ADD NEW QUESTION
// ═══════════════════════════════════════════════════════════════════════
function addNewQuestion() {
    // TODO: Aprire modal per creazione nuova domanda
    console.log('[Form Builder] Add new question');

    // Per ora mostra alert
    alert('Funzione in implementazione: aprirà modal per nuova domanda');
}

// ═══════════════════════════════════════════════════════════════════════
// EDIT QUESTION
// ═══════════════════════════════════════════════════════════════════════
function editQuestion(questionId) {
    console.log('[Form Builder] Edit question:', questionId);
    editingQuestionId = questionId;

    // TODO: Aprire modal per modifica
    alert(`Modifica domanda ${questionId} - Modal in implementazione`);
}

// ═══════════════════════════════════════════════════════════════════════
// DELETE QUESTION
// ═══════════════════════════════════════════════════════════════════════
async function deleteQuestion(questionId) {
    if (!confirm('Sei sicuro di voler eliminare questa domanda?')) {
        return;
    }

    console.log('[Form Builder] Delete question:', questionId);

    // TODO: Call API to delete
    try {
        const response = await fetch(`/recruiting/api/questions/${questionId}`, {
            method: 'DELETE'
        });

        if (response.ok) {
            questions = questions.filter(q => q.id !== questionId);
            renderQuestions();
            updateTotalWeight();
            showToast('Domanda eliminata', 'success');
        } else {
            throw new Error('Delete failed');
        }
    } catch (error) {
        console.error('[Form Builder] Error deleting question:', error);
        showToast('Errore eliminazione domanda', 'error');
    }
}

// ═══════════════════════════════════════════════════════════════════════
// SAVE ALL QUESTIONS
// ═══════════════════════════════════════════════════════════════════════
async function saveQuestions() {
    console.log('[Form Builder] Saving questions...');

    // Check weight
    const total = questions.reduce((sum, q) => sum + (parseFloat(q.weight) || 0), 0);

    if (Math.abs(total - 100) > 0.1) {
        if (!confirm(`Il peso totale è ${total.toFixed(1)}% invece di 100%. Vuoi salvare comunque?`)) {
            return;
        }
    }

    try {
        const response = await fetch(`/recruiting/offers/${OFFER_ID}/questions`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ questions })
        });

        const data = await response.json();

        if (data.success) {
            showToast('Domande salvate con successo!', 'success');
            await loadQuestions(); // Reload to get IDs
        } else {
            throw new Error(data.message || 'Save failed');
        }
    } catch (error) {
        console.error('[Form Builder] Error saving questions:', error);
        showToast('Errore salvataggio domande', 'error');
    }
}

// ═══════════════════════════════════════════════════════════════════════
// DRAG AND DROP
// ═══════════════════════════════════════════════════════════════════════
let draggedElement = null;
let draggedIndex = null;

function initDragAndDrop() {
    const cards = document.querySelectorAll('.question-card');

    cards.forEach((card, index) => {
        card.addEventListener('dragstart', handleDragStart);
        card.addEventListener('dragover', handleDragOver);
        card.addEventListener('drop', handleDrop);
        card.addEventListener('dragend', handleDragEnd);
    });
}

function handleDragStart(e) {
    draggedElement = e.currentTarget;
    draggedElement.classList.add('dragging');

    const questionId = parseInt(draggedElement.dataset.questionId);
    draggedIndex = questions.findIndex(q => q.id === questionId);

    e.dataTransfer.effectAllowed = 'move';
}

function handleDragOver(e) {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'move';

    const afterElement = getDragAfterElement(e.currentTarget.parentElement, e.clientY);
    const container = e.currentTarget.parentElement;

    if (afterElement == null) {
        container.appendChild(draggedElement);
    } else {
        container.insertBefore(draggedElement, afterElement);
    }
}

function handleDrop(e) {
    e.preventDefault();
    e.stopPropagation();

    // Reorder questions array
    const cards = Array.from(document.querySelectorAll('.question-card'));
    const newOrder = cards.map(card => parseInt(card.dataset.questionId));

    questions = newOrder.map((id, index) => {
        const q = questions.find(q => q.id === id);
        q.order = index;
        return q;
    });

    renderQuestions();
    updateTotalWeight();
}

function handleDragEnd(e) {
    draggedElement.classList.remove('dragging');
    draggedElement = null;
    draggedIndex = null;
}

function getDragAfterElement(container, y) {
    const draggableElements = [...container.querySelectorAll('.question-card:not(.dragging)')];

    return draggableElements.reduce((closest, child) => {
        const box = child.getBoundingClientRect();
        const offset = y - box.top - box.height / 2;

        if (offset < 0 && offset > closest.offset) {
            return { offset: offset, element: child };
        } else {
            return closest;
        }
    }, { offset: Number.NEGATIVE_INFINITY }).element;
}

// ═══════════════════════════════════════════════════════════════════════
// TOAST NOTIFICATION
// ═══════════════════════════════════════════════════════════════════════
function showToast(message, type = 'info') {
    // Check if Bootstrap toast exists
    const toastContainer = document.getElementById('toastContainer');
    if (!toastContainer) {
        // Fallback to alert
        alert(message);
        return;
    }

    // Create toast element
    const toastId = `toast-${Date.now()}`;
    const bgClass = type === 'success' ? 'bg-success' : type === 'error' ? 'bg-danger' : 'bg-info';

    const toastHTML = `
        <div id="${toastId}" class="toast align-items-center text-white ${bgClass} border-0" role="alert">
            <div class="d-flex">
                <div class="toast-body">
                    ${message}
                </div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
            </div>
        </div>
    `;

    toastContainer.insertAdjacentHTML('beforeend', toastHTML);

    const toastElement = document.getElementById(toastId);
    const toast = new bootstrap.Toast(toastElement);
    toast.show();

    // Remove after hidden
    toastElement.addEventListener('hidden.bs.toast', () => {
        toastElement.remove();
    });
}

// ═══════════════════════════════════════════════════════════════════════
// EXPORT
// ═══════════════════════════════════════════════════════════════════════
window.FormBuilder = {
    loadQuestions,
    renderQuestions,
    addNewQuestion,
    editQuestion,
    deleteQuestion,
    saveQuestions,
    updateTotalWeight
};

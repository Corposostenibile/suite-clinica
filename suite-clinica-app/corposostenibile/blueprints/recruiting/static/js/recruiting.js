/* ========================================
   Recruiting Module - JavaScript Functions
   ======================================== */

// Initialize module when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    initializeRecruitingModule();
});

function initializeRecruitingModule() {
    // Initialize tooltips
    initTooltips();
    
    // Initialize form validators
    initFormValidation();
    
    // Initialize date pickers
    initDatePickers();
    
    // Initialize charts if present
    if (document.getElementById('applicationChart')) {
        initCharts();
    }
    
    // Initialize drag and drop if present
    if (document.querySelector('.sortable-list')) {
        initSortable();
    }
    
    // Initialize file uploads
    initFileUploads();
    
    // Initialize search
    initSearch();
    
    // Initialize filters
    initFilters();
}

// ========================================
// Common Utilities
// ========================================

function initTooltips() {
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
}

function showLoading(element) {
    const loader = document.createElement('div');
    loader.className = 'text-center py-4';
    loader.innerHTML = `
        <div class="spinner-border text-primary" role="status">
            <span class="visually-hidden">Caricamento...</span>
        </div>
    `;
    element.innerHTML = '';
    element.appendChild(loader);
}

function showAlert(message, type = 'info') {
    const alertHtml = `
        <div class="alert alert-${type} alert-dismissible fade show animate-fadeIn" role="alert">
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        </div>
    `;
    
    const alertContainer = document.getElementById('alertContainer') || document.querySelector('.content');
    const alertElement = document.createElement('div');
    alertElement.innerHTML = alertHtml;
    alertContainer.insertBefore(alertElement.firstChild, alertContainer.firstChild);
    
    // Auto dismiss after 5 seconds
    setTimeout(() => {
        const alert = alertElement.querySelector('.alert');
        if (alert) {
            bootstrap.Alert.getInstance(alert)?.close();
        }
    }, 5000);
}

// ========================================
// Form Validation
// ========================================

function initFormValidation() {
    const forms = document.querySelectorAll('.needs-validation');
    
    Array.from(forms).forEach(form => {
        form.addEventListener('submit', event => {
            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
            }
            form.classList.add('was-validated');
        }, false);
    });
}

// ========================================
// Date Pickers
// ========================================

function initDatePickers() {
    const dateInputs = document.querySelectorAll('input[type="date"]');
    
    dateInputs.forEach(input => {
        // Set min date to today if not specified
        if (!input.min && input.dataset.minToday) {
            input.min = new Date().toISOString().split('T')[0];
        }
    });
}

// ========================================
// Charts
// ========================================

function initCharts() {
    // Applications by Source Chart
    const sourceChartEl = document.getElementById('sourceChart');
    if (sourceChartEl) {
        const sourceData = JSON.parse(sourceChartEl.dataset.chartData || '{}');
        new Chart(sourceChartEl.getContext('2d'), {
            type: 'doughnut',
            data: {
                labels: Object.keys(sourceData),
                datasets: [{
                    data: Object.values(sourceData),
                    backgroundColor: [
                        '#0077b5', // LinkedIn
                        '#1877f2', // Facebook
                        '#e4405f', // Instagram
                        '#718096', // Direct
                    ]
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom'
                    }
                }
            }
        });
    }
    
    // Applications Timeline Chart
    const timelineChartEl = document.getElementById('timelineChart');
    if (timelineChartEl) {
        const timelineData = JSON.parse(timelineChartEl.dataset.chartData || '{}');
        new Chart(timelineChartEl.getContext('2d'), {
            type: 'line',
            data: {
                labels: timelineData.labels,
                datasets: [{
                    label: 'Candidature',
                    data: timelineData.applications,
                    borderColor: '#0066cc',
                    backgroundColor: 'rgba(0, 102, 204, 0.1)',
                    tension: 0.4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            stepSize: 1
                        }
                    }
                }
            }
        });
    }
}

// ========================================
// Drag and Drop / Sortable
// ========================================

function initSortable() {
    // Questions sortable
    const questionsList = document.getElementById('questionsList');
    if (questionsList) {
        new Sortable(questionsList, {
            animation: 150,
            handle: '.drag-handle',
            ghostClass: 'bg-light',
            dragClass: 'dragging',
            onEnd: function(evt) {
                updateQuestionOrder();
            }
        });
    }
    
    // Kanban columns
    document.querySelectorAll('.kanban-cards').forEach(column => {
        new Sortable(column, {
            group: 'kanban',
            animation: 150,
            ghostClass: 'bg-light',
            dragClass: 'dragging',
            onEnd: function(evt) {
                const applicationId = evt.item.dataset.applicationId;
                const newStageId = evt.to.dataset.stage;
                updateApplicationStage(applicationId, newStageId);
            }
        });
    });
}

function updateQuestionOrder() {
    const questions = document.querySelectorAll('.question-item');
    const order = Array.from(questions).map((q, index) => ({
        id: q.dataset.questionId,
        order: index + 1
    }));
    
    fetch('/recruiting/api/questions/reorder', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCsrfToken()
        },
        body: JSON.stringify({ order })
    }).then(response => {
        if (response.ok) {
            showAlert('Ordine aggiornato', 'success');
        }
    });
}

async function updateApplicationStage(applicationId, stageId) {
    try {
        const response = await fetch('/recruiting/api/kanban/move', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCsrfToken()
            },
            body: JSON.stringify({
                application_id: applicationId,
                stage_id: stageId
            })
        });
        
        if (response.ok) {
            showAlert('Candidato spostato', 'success');
            updateKanbanCounts();
        } else {
            showAlert('Errore nello spostamento', 'danger');
            location.reload();
        }
    } catch (error) {
        showAlert('Errore di connessione', 'danger');
        location.reload();
    }
}

function updateKanbanCounts() {
    document.querySelectorAll('.kanban-column').forEach(column => {
        const count = column.querySelectorAll('.kanban-card').length;
        column.querySelector('.kanban-column-count').textContent = count;
    });
}

// ========================================
// File Uploads
// ========================================

function initFileUploads() {
    const fileInputs = document.querySelectorAll('input[type="file"]');
    
    fileInputs.forEach(input => {
        const uploadArea = input.closest('.file-upload-area');
        if (!uploadArea) return;
        
        // Click to upload
        uploadArea.addEventListener('click', () => input.click());
        
        // Drag and drop
        uploadArea.addEventListener('dragover', (e) => {
            e.preventDefault();
            uploadArea.classList.add('dragover');
        });
        
        uploadArea.addEventListener('dragleave', () => {
            uploadArea.classList.remove('dragover');
        });
        
        uploadArea.addEventListener('drop', (e) => {
            e.preventDefault();
            uploadArea.classList.remove('dragover');
            
            const files = e.dataTransfer.files;
            if (files.length > 0) {
                input.files = files;
                handleFileSelect(input, files[0]);
            }
        });
        
        // File selected
        input.addEventListener('change', (e) => {
            if (e.target.files.length > 0) {
                handleFileSelect(input, e.target.files[0]);
            }
        });
    });
}

function handleFileSelect(input, file) {
    const maxSize = 10 * 1024 * 1024; // 10MB
    
    if (file.size > maxSize) {
        showAlert('Il file è troppo grande. Massimo 10MB.', 'danger');
        input.value = '';
        return;
    }
    
    // Show file info
    const fileInfo = input.parentElement.querySelector('.file-info');
    if (fileInfo) {
        fileInfo.innerHTML = `
            <i class="ri-file-text-line me-2"></i>
            ${file.name} (${formatFileSize(file.size)})
            <button type="button" class="btn-close btn-sm float-end" onclick="clearFileInput('${input.id}')"></button>
        `;
        fileInfo.style.display = 'block';
    }
}

function clearFileInput(inputId) {
    const input = document.getElementById(inputId);
    if (input) {
        input.value = '';
        const fileInfo = input.parentElement.querySelector('.file-info');
        if (fileInfo) {
            fileInfo.style.display = 'none';
        }
    }
}

function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
}

// ========================================
// Search & Filters
// ========================================

function initSearch() {
    const searchInputs = document.querySelectorAll('.search-input');
    
    searchInputs.forEach(input => {
        let debounceTimer;
        
        input.addEventListener('input', (e) => {
            clearTimeout(debounceTimer);
            debounceTimer = setTimeout(() => {
                performSearch(e.target.value, e.target.dataset.target);
            }, 300);
        });
    });
}

function performSearch(query, target) {
    const targetElement = document.getElementById(target);
    if (!targetElement) return;
    
    const items = targetElement.querySelectorAll('[data-searchable]');
    const lowerQuery = query.toLowerCase();
    
    items.forEach(item => {
        const searchText = item.dataset.searchable.toLowerCase();
        if (searchText.includes(lowerQuery)) {
            item.style.display = '';
        } else {
            item.style.display = 'none';
        }
    });
}

function initFilters() {
    const filterSelects = document.querySelectorAll('.filter-select');
    
    filterSelects.forEach(select => {
        select.addEventListener('change', () => {
            applyFilters();
        });
    });
}

function applyFilters() {
    const filters = {};
    
    document.querySelectorAll('.filter-select').forEach(select => {
        if (select.value) {
            filters[select.dataset.filter] = select.value;
        }
    });
    
    const params = new URLSearchParams(filters);
    window.location.search = params.toString();
}

// ========================================
// API Functions
// ========================================

async function deleteItem(type, id, confirmMessage) {
    if (!confirm(confirmMessage || 'Sei sicuro di voler eliminare questo elemento?')) {
        return;
    }
    
    try {
        const response = await fetch(`/recruiting/api/${type}/${id}`, {
            method: 'DELETE',
            headers: {
                'X-CSRFToken': getCsrfToken()
            }
        });
        
        if (response.ok) {
            showAlert('Elemento eliminato', 'success');
            setTimeout(() => location.reload(), 1000);
        } else {
            showAlert('Errore durante l\'eliminazione', 'danger');
        }
    } catch (error) {
        showAlert('Errore di connessione', 'danger');
    }
}

async function duplicateTemplate(templateId) {
    const name = prompt('Nome del nuovo template:');
    if (!name) return;
    
    try {
        const response = await fetch(`/recruiting/api/templates/${templateId}/duplicate`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCsrfToken()
            },
            body: JSON.stringify({ name })
        });
        
        if (response.ok) {
            showAlert('Template duplicato', 'success');
            setTimeout(() => location.reload(), 1000);
        } else {
            showAlert('Errore durante la duplicazione', 'danger');
        }
    } catch (error) {
        showAlert('Errore di connessione', 'danger');
    }
}

// ========================================
// Question Builder
// ========================================

function addQuestion() {
    const modal = new bootstrap.Modal(document.getElementById('questionModal'));
    document.getElementById('questionForm').reset();
    document.getElementById('questionId').value = '';
    modal.show();
}

function editQuestion(questionId) {
    fetch(`/recruiting/api/questions/${questionId}`)
        .then(response => response.json())
        .then(question => {
            document.getElementById('questionId').value = question.id;
            document.getElementById('questionText').value = question.question_text;
            document.getElementById('questionType').value = question.question_type;
            document.getElementById('questionWeight').value = question.weight;
            document.getElementById('questionRequired').checked = question.is_required;
            document.getElementById('expectedAnswer').value = question.expected_answer || '';
            
            // Show/hide expected answer field based on type
            toggleExpectedAnswer();
            
            const modal = new bootstrap.Modal(document.getElementById('questionModal'));
            modal.show();
        });
}

function saveQuestion() {
    const form = document.getElementById('questionForm');
    const formData = new FormData(form);
    const questionId = document.getElementById('questionId').value;
    
    const url = questionId 
        ? `/recruiting/api/questions/${questionId}` 
        : '/recruiting/api/questions';
    
    const method = questionId ? 'PUT' : 'POST';
    
    fetch(url, {
        method: method,
        headers: {
            'X-CSRFToken': getCsrfToken()
        },
        body: formData
    }).then(response => {
        if (response.ok) {
            showAlert('Domanda salvata', 'success');
            setTimeout(() => location.reload(), 1000);
        } else {
            showAlert('Errore nel salvataggio', 'danger');
        }
    });
}

function deleteQuestion(questionId) {
    deleteItem('questions', questionId, 'Eliminare questa domanda?');
}

function toggleExpectedAnswer() {
    const questionType = document.getElementById('questionType').value;
    const expectedAnswerGroup = document.getElementById('expectedAnswerGroup');
    
    const typesWithExpected = ['text', 'textarea', 'number', 'select', 'radio', 'yes_no'];
    
    if (typesWithExpected.includes(questionType)) {
        expectedAnswerGroup.style.display = 'block';
    } else {
        expectedAnswerGroup.style.display = 'none';
    }
}

function updateWeightTotal() {
    const weights = document.querySelectorAll('.question-weight');
    let total = 0;
    
    weights.forEach(input => {
        total += parseInt(input.value) || 0;
    });
    
    const totalElement = document.getElementById('totalWeight');
    if (totalElement) {
        totalElement.textContent = total + '%';
        totalElement.className = total === 100 ? 'text-success' : 'text-danger';
    }
}

// ========================================
// Onboarding Functions
// ========================================

function toggleTask(taskId, checklistId) {
    const checkbox = document.getElementById(`task_${taskId}`);
    const isCompleted = checkbox.checked;
    
    fetch(`/recruiting/api/onboarding/${checklistId}/tasks/${taskId}`, {
        method: 'PATCH',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCsrfToken()
        },
        body: JSON.stringify({ completed: isCompleted })
    }).then(response => {
        if (response.ok) {
            updateOnboardingProgress(checklistId);
            const taskItem = checkbox.closest('.onboarding-task');
            if (isCompleted) {
                taskItem.classList.add('completed');
            } else {
                taskItem.classList.remove('completed');
            }
        }
    });
}

function updateOnboardingProgress(checklistId) {
    fetch(`/recruiting/api/onboarding/${checklistId}/progress`)
        .then(response => response.json())
        .then(data => {
            const progressBar = document.getElementById('progressBar');
            if (progressBar) {
                progressBar.style.width = data.percentage + '%';
                progressBar.textContent = data.percentage + '%';
                
                // Update color based on progress
                progressBar.className = 'progress-bar';
                if (data.percentage >= 75) {
                    progressBar.classList.add('bg-success');
                } else if (data.percentage >= 50) {
                    progressBar.classList.add('bg-warning');
                } else {
                    progressBar.classList.add('bg-danger');
                }
            }
        });
}

// ========================================
// Utility Functions
// ========================================

function getCsrfToken() {
    return document.querySelector('meta[name="csrf-token"]')?.content || 
           document.querySelector('input[name="csrf_token"]')?.value || '';
}

function copyToClipboard(text, button) {
    navigator.clipboard.writeText(text).then(() => {
        const originalText = button.innerHTML;
        button.innerHTML = '<i class="ri-check-line"></i> Copiato!';
        button.classList.add('btn-success');
        
        setTimeout(() => {
            button.innerHTML = originalText;
            button.classList.remove('btn-success');
        }, 2000);
    });
}

function exportData(type, format) {
    const url = `/recruiting/api/export/${type}?format=${format}`;
    window.location.href = url;
}

function printPage() {
    window.print();
}

// ========================================
// Real-time Updates (WebSocket)
// ========================================

function initWebSocket() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const ws = new WebSocket(`${protocol}//${window.location.host}/ws/recruiting`);
    
    ws.onmessage = function(event) {
        const data = JSON.parse(event.data);
        
        if (data.type === 'new_application') {
            showAlert(`Nuova candidatura ricevuta: ${data.name}`, 'info');
            updateApplicationCount();
        } else if (data.type === 'stage_update') {
            updateKanbanCard(data.application_id, data.stage_id);
        }
    };
    
    ws.onerror = function(error) {
        console.error('WebSocket error:', error);
    };
}

function updateApplicationCount() {
    const countElement = document.getElementById('applicationCount');
    if (countElement) {
        const currentCount = parseInt(countElement.textContent) || 0;
        countElement.textContent = currentCount + 1;
        countElement.classList.add('animate-pulse');
    }
}

// ========================================
// Export functions for global use
// ========================================

window.RecruitingModule = {
    init: initializeRecruitingModule,
    showAlert,
    showLoading,
    deleteItem,
    duplicateTemplate,
    addQuestion,
    editQuestion,
    saveQuestion,
    deleteQuestion,
    toggleTask,
    copyToClipboard,
    exportData,
    printPage
};
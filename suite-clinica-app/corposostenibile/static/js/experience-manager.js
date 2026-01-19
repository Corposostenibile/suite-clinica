// Experience Manager - Complete Functions for Team Module

// Store current experience data
window.currentExperienceData = {
    experiences: [],
    referees: []
};

// Debug function
function debugLog(message) {
    console.log('[Experience Manager]', message);
}

// Wait for page to be fully loaded
document.addEventListener('DOMContentLoaded', function() {
    debugLog('Experience Manager loaded');
});

// ========== Generic Experience Modal Creator ==========
function openExperienceModal(type, editMode = false, index = null) {
    const configs = {
        'experience': {
            title: 'Esperienza Lavorativa',
            fields: [
                { id: 'exp_company', label: 'Azienda', type: 'text', required: true },
                { id: 'exp_role', label: 'Ruolo', type: 'text', required: true },
                { id: 'exp_start_date', label: 'Data Inizio', type: 'date', required: true },
                { id: 'exp_end_date', label: 'Data Fine', type: 'date', placeholder: 'Lasciare vuoto se attualmente in corso' },
                { id: 'exp_responsibilities', label: 'Responsabilità principali', type: 'textarea', rows: 3, placeholder: 'Descrivi le principali responsabilità (una per riga)' }
            ],
            dataKey: 'experiences'
        },
        'referee': {
            title: 'Referenza Professionale',
            fields: [
                { id: 'ref_name', label: 'Nome e Cognome', type: 'text', required: true },
                { id: 'ref_company', label: 'Azienda', type: 'text', required: true },
                { id: 'ref_role', label: 'Ruolo', type: 'text', required: true },
                { id: 'ref_phone', label: 'Telefono', type: 'tel' },
                { id: 'ref_email', label: 'Email', type: 'email' }
            ],
            dataKey: 'referees'
        }
    };
    
    const config = configs[type];
    if (!config) return;
    
    const modalId = `${type}Modal`;
    const formId = `form-${type}`;
    
    // Create modal HTML
    let fieldsHtml = '';
    config.fields.forEach(field => {
        fieldsHtml += `
            <div class="mb-3">
                <label class="form-label">${field.label}${field.required ? ' *' : ''}</label>`;
        
        if (field.type === 'textarea') {
            fieldsHtml += `<textarea class="form-control" id="${field.id}" 
                rows="${field.rows || 3}"
                ${field.placeholder ? `placeholder="${field.placeholder}"` : ''}
                ${field.required ? 'required' : ''}></textarea>`;
        } else {
            fieldsHtml += `<input type="${field.type}" class="form-control" id="${field.id}" 
                ${field.placeholder ? `placeholder="${field.placeholder}"` : ''}
                ${field.required ? 'required' : ''}>`;
        }
        
        fieldsHtml += `</div>`;
    });
    
    const modalHtml = `
    <div class="modal fade" id="${modalId}" tabindex="-1">
        <div class="modal-dialog modal-lg">
            <div class="modal-content">
                <div class="modal-header">
                    <h5 class="modal-title">${editMode ? 'Modifica' : 'Aggiungi'} ${config.title}</h5>
                    <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                </div>
                <form id="${formId}">
                    <div class="modal-body">
                        ${fieldsHtml}
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Annulla</button>
                        <button type="submit" class="btn btn-primary">Salva</button>
                    </div>
                </form>
            </div>
        </div>
    </div>`;
    
    // Remove existing modal if present
    const existingModal = document.getElementById(modalId);
    if (existingModal) {
        existingModal.remove();
    }
    
    // Add modal to DOM
    document.body.insertAdjacentHTML('beforeend', modalHtml);
    
    // Fill data if editing
    if (editMode && index !== null && window.currentExperienceData) {
        const data = window.currentExperienceData[config.dataKey][index];
        
        if (data) {
            config.fields.forEach(field => {
                const element = document.getElementById(field.id);
                if (element) {
                    const fieldKey = field.id.split('_')[1]; // Extract key from id
                    if (field.type === 'textarea' && fieldKey === 'responsibilities' && Array.isArray(data[fieldKey])) {
                        element.value = data[fieldKey].join('\n');
                    } else {
                        element.value = data[fieldKey] || '';
                    }
                }
            });
        }
    }
    
    // Add submit handler
    document.getElementById(formId).addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const formData = {};
        config.fields.forEach(field => {
            const element = document.getElementById(field.id);
            const fieldKey = field.id.split('_')[1];
            
            if (field.type === 'textarea' && fieldKey === 'responsibilities') {
                // Split responsibilities by newline
                formData[fieldKey] = element.value
                    .split('\n')
                    .filter(r => r.trim())
                    .map(r => r.trim());
            } else {
                formData[fieldKey] = element.value || null;
            }
        });
        
        const action = editMode ? 'edit' : 'add';
        
        if (editMode && index !== null) {
            await saveExperienceData(config.dataKey, formData, 'edit', index);
        } else {
            await saveExperienceData(config.dataKey, formData, 'add');
        }
        
        // Close modal
        const modalElement = document.getElementById(modalId);
        if (modalElement) {
            if (window.bootstrap && window.bootstrap.Modal) {
                const modal = bootstrap.Modal.getInstance(modalElement);
                if (modal) {
                    modal.hide();
                } else {
                    modalElement.style.display = 'none';
                    modalElement.classList.remove('show');
                }
            } else {
                modalElement.style.display = 'none';
                modalElement.classList.remove('show');
            }
        }
    });
    
    // Show modal with fallback
    const modalElement = document.getElementById(modalId);
    if (modalElement) {
        if (window.bootstrap && window.bootstrap.Modal) {
            const modal = new bootstrap.Modal(modalElement);
            modal.show();
        } else {
            // Fallback if Bootstrap is not available
            debugLog('Bootstrap not available, showing modal manually');
            modalElement.style.display = 'block';
            modalElement.classList.add('show');
        }
    } else {
        debugLog('Modal element not found: ' + modalId);
    }
    
    // Store edit context
    window.currentExpEditType = type;
    window.currentExpEditIndex = index;
    window.currentExpEditMode = editMode;
}

// ========== Add Functions ==========
function addExperience() {
    debugLog('addExperience called');
    openExperienceModal('experience', false);
}

function addReferee() {
    debugLog('addReferee called');
    openExperienceModal('referee', false);
}

// ========== Edit Functions ==========
function editExperience(index) {
    debugLog('editExperience called with index: ' + index);
    openExperienceModal('experience', true, index);
}

function editReferee(index) {
    debugLog('editReferee called with index: ' + index);
    openExperienceModal('referee', true, index);
}

// ========== Remove Functions ==========
async function removeExperience(index) {
    if (confirm('Sei sicuro di voler eliminare questa esperienza?')) {
        await saveExperienceData('experiences', index, 'remove');
    }
}

async function removeReferee(index) {
    if (confirm('Sei sicuro di voler eliminare questa referenza?')) {
        await saveExperienceData('referees', index, 'remove');
    }
}

// ========== Save Experience Data ==========
async function saveExperienceData(type, data, action, index = null) {
    try {
        // Get user ID from the page
        const userId = document.querySelector('[data-user-id]')?.dataset.userId || 
                      document.querySelector('#form-anagrafica')?.dataset.userId;
        
        if (!userId) {
            throw new Error('User ID non trovato');
        }
        
        // Get CSRF token
        const csrfToken = document.querySelector('meta[name="csrf-token"]')?.content || 
                          document.querySelector('[name="csrf_token"]')?.value;
        
        let requestData = {
            type: type,
            action: action
        };
        
        if (action === 'edit' && index !== null) {
            // For edit, send the index and the updated data
            requestData.data = { index: index, data: data };
        } else {
            requestData.data = data;
        }
        
        const response = await fetch(`/team/${userId}/experience`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken
            },
            body: JSON.stringify(requestData)
        });
        
        const result = await response.json();
        
        if (result.success) {
            showAlert('success', 'Salvato con successo!');
            setTimeout(() => {
                // Save active tab before reload
                const activeTab = document.querySelector('.nav-link.active[data-bs-toggle="pill"]');
                if (activeTab) {
                    localStorage.setItem('activeTab_user_' + userId, activeTab.id);
                }
                location.reload();
            }, 1500);
        } else {
            throw new Error(result.message || 'Errore durante il salvataggio');
        }
    } catch (error) {
        console.error('Error:', error);
        showAlert('danger', 'Errore: ' + error.message);
    }
}

// ========== Utility Functions ==========
function showAlert(type, message) {
    const alertHtml = `
        <div class="alert alert-${type} alert-dismissible fade show position-fixed top-0 start-50 translate-middle-x mt-3" 
             style="z-index: 9999;" role="alert">
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        </div>`;
    
    document.body.insertAdjacentHTML('beforeend', alertHtml);
    
    // Auto-remove after 5 seconds
    setTimeout(() => {
        const alert = document.querySelector('.alert');
        if (alert) {
            alert.remove();
        }
    }, 5000);
}
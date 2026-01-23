// Education Manager - Complete Functions for Team Module

// ========== Generic Education Modal Creator ==========
function openEducationModal(type, editMode = false, index = null) {
    const configs = {
        'degree': {
            title: 'Laurea',
            fields: [
                { id: 'degree_type', label: 'Tipo Laurea', type: 'select', options: ['Triennale', 'Magistrale', 'Magistrale a Ciclo Unico'], required: true },
                { id: 'degree_course', label: 'Corso di Studio', type: 'text', required: true },
                { id: 'degree_university', label: 'Università', type: 'text', required: true },
                { id: 'degree_year', label: 'Anno Conseguimento', type: 'number', min: 1900, max: 2030, required: true },
                { id: 'degree_grade', label: 'Voto', type: 'text', placeholder: 'es. 110/110 e lode' }
            ],
            dataKey: 'degrees'
        },
        'master': {
            title: 'Master',
            fields: [
                { id: 'master_name', label: 'Nome Master', type: 'text', required: true },
                { id: 'master_institute', label: 'Istituto', type: 'text', required: true },
                { id: 'master_year', label: 'Anno', type: 'number', min: 1900, max: 2030, required: true },
                { id: 'master_duration', label: 'Durata (mesi)', type: 'number', min: 1 }
            ],
            dataKey: 'masters'
        },
        'course': {
            title: 'Corso di Formazione',
            fields: [
                { id: 'course_name', label: 'Nome Corso', type: 'text', required: true },
                { id: 'course_institute', label: 'Ente Formatore', type: 'text', required: true },
                { id: 'course_year', label: 'Anno', type: 'number', min: 1900, max: 2030, required: true },
                { id: 'course_hours', label: 'Ore', type: 'number', min: 1 }
            ],
            dataKey: 'courses'
        },
        'certification': {
            title: 'Certificazione Professionale',
            fields: [
                { id: 'cert_name', label: 'Nome Certificazione', type: 'text', required: true },
                { id: 'cert_issuer', label: 'Ente Certificatore', type: 'text', required: true },
                { id: 'cert_date', label: 'Data Conseguimento', type: 'date', required: true },
                { id: 'cert_expiry', label: 'Data Scadenza', type: 'date' }
            ],
            dataKey: 'certifications'
        },
        'phd': {
            title: 'Dottorato di Ricerca',
            fields: [
                { id: 'phd_title', label: 'Titolo Tesi', type: 'text', required: true },
                { id: 'phd_university', label: 'Università', type: 'text', required: true },
                { id: 'phd_year', label: 'Anno Conseguimento', type: 'number', min: 1900, max: 2030, required: true },
                { id: 'phd_supervisor', label: 'Relatore', type: 'text' }
            ],
            dataKey: 'phd'
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
        
        if (field.type === 'select') {
            fieldsHtml += `<select class="form-control" id="${field.id}" ${field.required ? 'required' : ''}>
                <option value="">Seleziona...</option>`;
            field.options.forEach(opt => {
                fieldsHtml += `<option value="${opt}">${opt}</option>`;
            });
            fieldsHtml += `</select>`;
        } else {
            fieldsHtml += `<input type="${field.type}" class="form-control" id="${field.id}" 
                ${field.placeholder ? `placeholder="${field.placeholder}"` : ''}
                ${field.min ? `min="${field.min}"` : ''}
                ${field.max ? `max="${field.max}"` : ''}
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
    if (editMode && index !== null && window.currentEducationData) {
        const data = config.dataKey === 'phd' ? 
            window.currentEducationData[config.dataKey] :
            window.currentEducationData[config.dataKey][index];
            
        if (data) {
            config.fields.forEach(field => {
                const element = document.getElementById(field.id);
                if (element) {
                    const fieldKey = field.id.split('_')[1]; // Extract key from id
                    element.value = data[fieldKey] || '';
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
            formData[fieldKey] = element.value;
        });
        
        const action = editMode ? 'edit' : 'add';
        
        if (config.dataKey === 'phd') {
            await saveEducationData('phd', formData, action);
        } else {
            if (editMode && index !== null) {
                await saveEducationData(config.dataKey, formData, 'edit', index);
            } else {
                await saveEducationData(config.dataKey, formData, 'add');
            }
        }
        
        // Close modal
        const modal = bootstrap.Modal.getInstance(document.getElementById(modalId));
        modal.hide();
    });
    
    // Show modal
    const modal = new bootstrap.Modal(document.getElementById(modalId));
    modal.show();
    
    // Store edit context
    window.currentEditType = type;
    window.currentEditIndex = index;
    window.currentEditMode = editMode;
}

// ========== Edit Functions ==========
function editDegree(index) {
    openEducationModal('degree', true, index);
}

function editMaster(index) {
    openEducationModal('master', true, index);
}

function editCourse(index) {
    openEducationModal('course', true, index);
}

function editCertification(index) {
    openEducationModal('certification', true, index);
}

function editPhD() {
    openEducationModal('phd', true, 0);
}

// ========== Remove Functions ==========
async function removeDegree(index) {
    if (confirm('Sei sicuro di voler eliminare questa laurea?')) {
        await saveEducationData('degrees', index, 'remove');
    }
}

async function removeMaster(index) {
    if (confirm('Sei sicuro di voler eliminare questo master?')) {
        await saveEducationData('masters', index, 'remove');
    }
}

async function removeCourse(index) {
    if (confirm('Sei sicuro di voler eliminare questo corso?')) {
        await saveEducationData('courses', index, 'remove');
    }
}

async function removeCertification(index) {
    if (confirm('Sei sicuro di voler eliminare questa certificazione?')) {
        await saveEducationData('certifications', index, 'remove');
    }
}

async function removePhD() {
    if (confirm('Sei sicuro di voler eliminare il dottorato?')) {
        await saveEducationData('phd', null, 'remove');
    }
}

// ========== Upload Education Attachment (10MB limit) ==========
async function uploadEducationAttachment(type, index = null) {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = '.pdf,.jpg,.jpeg,.png,.doc,.docx';
    
    input.onchange = async (e) => {
        const file = e.target.files[0];
        if (!file) return;
        
        // Check file size (10MB max)
        if (file.size > 10 * 1024 * 1024) {
            showAlert('danger', 'File troppo grande. Max 10MB.');
            return;
        }
        
        const formData = new FormData();
        formData.append('file', file);
        formData.append('type', type);
        if (index !== null) {
            formData.append('index', index);
        }
        
        // Get CSRF token
        const csrfToken = document.querySelector('meta[name="csrf-token"]')?.content || 
                          document.querySelector('[name="csrf_token"]')?.value;
        
        try {
            const response = await fetch(`/team/${userId}/upload-education-attachment`, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': csrfToken
                },
                body: formData
            });
            
            if (!response.ok) {
                throw new Error(`Upload failed: ${response.status}`);
            }
            
            const result = await response.json();
            if (result.success) {
                showAlert('success', 'Allegato caricato con successo');
                setTimeout(() => {
                    // Save active tab before reload
                    const activeTab = document.querySelector('.nav-link.active[data-bs-toggle="pill"]');
                    if (activeTab) {
                        localStorage.setItem('activeTab_user_' + userId, activeTab.id);
                    }
                    location.reload();
                }, 1500);
            } else {
                throw new Error(result.message || 'Errore durante il caricamento');
            }
        } catch (error) {
            console.error('Upload error:', error);
            showAlert('danger', 'Errore upload: ' + error.message);
        }
    };
    
    input.click();
}
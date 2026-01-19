/**
 * Team Profile Editor
 * Advanced profile management system with auto-save, validation, and real-time updates
 */

class TeamProfileEditor {
    constructor(config) {
        this.userId = config.userId;
        this.canEdit = config.canEdit;
        this.csrfToken = config.csrfToken;
        this.endpoints = config.endpoints || {
            update: `/team/${config.userId}/update`,
            updateField: `/team/${config.userId}/update-field`,
            uploadAvatar: `/team/${config.userId}/upload-avatar`,
            uploadDocument: `/team/${config.userId}/upload-document`
        };
        
        // State management
        this.originalData = {};
        this.pendingChanges = {};
        this.saveTimer = null;
        this.saveDelay = 1000; // 1 second debounce
        
        // Initialize
        this.init();
    }
    
    init() {
        this.cacheOriginalData();
        this.setupEventListeners();
        this.setupAutoSave();
        this.setupValidation();
        this.setupTabSystem();
        this.setupEditableFields();
        this.setupFileUploads();
        this.setupSkillsManager();
        this.setupDatePickers();
        this.setupSelect2();
        this.setupTooltips();
    }
    
    // Cache original form data
    cacheOriginalData() {
        document.querySelectorAll('form').forEach(form => {
            const formData = new FormData(form);
            this.originalData[form.id] = Object.fromEntries(formData);
        });
    }
    
    // Setup event listeners
    setupEventListeners() {
        // Track changes
        document.addEventListener('input', this.handleInputChange.bind(this));
        document.addEventListener('change', this.handleInputChange.bind(this));
        
        // Keyboard shortcuts
        document.addEventListener('keydown', (e) => {
            if ((e.ctrlKey || e.metaKey) && e.key === 's') {
                e.preventDefault();
                this.saveAllChanges();
            }
        });
        
        // Prevent accidental navigation with unsaved changes
        window.addEventListener('beforeunload', (e) => {
            if (Object.keys(this.pendingChanges).length > 0) {
                e.preventDefault();
                e.returnValue = 'Hai modifiche non salvate. Vuoi davvero uscire?';
            }
        });
    }
    
    // Handle input changes
    handleInputChange(event) {
        const input = event.target;
        if (!input.name || input.closest('.no-autosave')) return;
        
        const form = input.closest('form');
        if (!form) return;
        
        // Track change
        if (!this.pendingChanges[form.id]) {
            this.pendingChanges[form.id] = {};
        }
        
        this.pendingChanges[form.id][input.name] = input.value;
        
        // Update UI to show unsaved changes
        this.markFieldAsChanged(input);
        
        // Trigger auto-save
        this.scheduleAutoSave();
    }
    
    // Mark field as changed
    markFieldAsChanged(input) {
        input.classList.add('has-changes');
        
        const fieldGroup = input.closest('.form-field');
        if (fieldGroup) {
            fieldGroup.classList.add('has-changes');
        }
        
        // Show save indicator
        this.updateSaveIndicator('pending');
    }
    
    // Auto-save functionality
    setupAutoSave() {
        if (!this.canEdit) return;
        
        // Enable auto-save toggle
        const autoSaveToggle = document.getElementById('autoSaveToggle');
        if (autoSaveToggle) {
            autoSaveToggle.addEventListener('change', (e) => {
                localStorage.setItem('autoSaveEnabled', e.target.checked);
            });
            
            // Load saved preference
            const autoSaveEnabled = localStorage.getItem('autoSaveEnabled') !== 'false';
            autoSaveToggle.checked = autoSaveEnabled;
        }
    }
    
    scheduleAutoSave() {
        const autoSaveEnabled = localStorage.getItem('autoSaveEnabled') !== 'false';
        if (!autoSaveEnabled) return;
        
        // Clear existing timer
        if (this.saveTimer) {
            clearTimeout(this.saveTimer);
        }
        
        // Schedule new save
        this.saveTimer = setTimeout(() => {
            this.autoSave();
        }, this.saveDelay);
    }
    
    async autoSave() {
        if (Object.keys(this.pendingChanges).length === 0) return;
        
        this.updateSaveIndicator('saving');
        
        try {
            const promises = Object.entries(this.pendingChanges).map(([formId, data]) => {
                return this.saveFormData(formId, data);
            });
            
            await Promise.all(promises);
            
            this.pendingChanges = {};
            this.updateSaveIndicator('saved');
            this.showNotification('success', 'Modifiche salvate automaticamente');
            
            // Clear changed markers
            document.querySelectorAll('.has-changes').forEach(el => {
                el.classList.remove('has-changes');
            });
        } catch (error) {
            this.updateSaveIndicator('error');
            this.showNotification('error', 'Errore durante il salvataggio automatico');
        }
    }
    
    // Save form data
    async saveFormData(formId, data) {
        const response = await fetch(this.endpoints.update, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': this.csrfToken
            },
            body: JSON.stringify({
                form_id: formId,
                data: data
            })
        });
        
        if (!response.ok) {
            throw new Error('Save failed');
        }
        
        return response.json();
    }
    
    // Manual save all changes
    async saveAllChanges() {
        const forms = document.querySelectorAll('form:not(.no-save)');
        const promises = [];
        
        forms.forEach(form => {
            if (form.checkValidity()) {
                const formData = new FormData(form);
                const data = Object.fromEntries(formData);
                promises.push(this.saveFormData(form.id, data));
            } else {
                form.reportValidity();
            }
        });
        
        if (promises.length === 0) {
            this.showNotification('info', 'Nessuna modifica da salvare');
            return;
        }
        
        this.updateSaveIndicator('saving');
        
        try {
            await Promise.all(promises);
            this.pendingChanges = {};
            this.updateSaveIndicator('saved');
            this.showNotification('success', 'Tutte le modifiche sono state salvate');
            
            // Clear changed markers
            document.querySelectorAll('.has-changes').forEach(el => {
                el.classList.remove('has-changes');
            });
        } catch (error) {
            this.updateSaveIndicator('error');
            this.showNotification('error', 'Alcune modifiche non sono state salvate');
        }
    }
    
    // Validation setup
    setupValidation() {
        // Codice Fiscale validation
        document.querySelectorAll('input[name="codice_fiscale"]').forEach(input => {
            input.addEventListener('input', () => {
                const cf = input.value.toUpperCase();
                input.value = cf;
                
                if (cf && !this.validateCodiceFiscale(cf)) {
                    input.setCustomValidity('Codice fiscale non valido');
                    input.classList.add('is-invalid');
                } else {
                    input.setCustomValidity('');
                    input.classList.remove('is-invalid');
                }
            });
        });
        
        // Partita IVA validation
        document.querySelectorAll('input[name="partita_iva"]').forEach(input => {
            input.addEventListener('input', () => {
                const piva = input.value;
                
                if (piva && !this.validatePartitaIVA(piva)) {
                    input.setCustomValidity('Partita IVA non valida');
                    input.classList.add('is-invalid');
                } else {
                    input.setCustomValidity('');
                    input.classList.remove('is-invalid');
                }
            });
        });
        
        // Email validation
        document.querySelectorAll('input[type="email"]').forEach(input => {
            input.addEventListener('input', () => {
                if (!this.validateEmail(input.value)) {
                    input.setCustomValidity('Email non valida');
                    input.classList.add('is-invalid');
                } else {
                    input.setCustomValidity('');
                    input.classList.remove('is-invalid');
                }
            });
        });
        
        // Phone validation
        document.querySelectorAll('input[type="tel"]').forEach(input => {
            input.addEventListener('input', () => {
                const phone = input.value.replace(/\D/g, '');
                if (phone && phone.length < 9) {
                    input.setCustomValidity('Numero di telefono non valido');
                    input.classList.add('is-invalid');
                } else {
                    input.setCustomValidity('');
                    input.classList.remove('is-invalid');
                }
            });
        });
    }
    
    // Validation functions
    validateCodiceFiscale(cf) {
        if (cf.length !== 16) return false;
        
        const pattern = /^[A-Z]{6}[0-9]{2}[A-Z][0-9]{2}[A-Z][0-9]{3}[A-Z]$/;
        if (!pattern.test(cf)) return false;
        
        // Advanced validation can be added here
        return true;
    }
    
    validatePartitaIVA(piva) {
        if (piva.length !== 11) return false;
        if (!/^\d{11}$/.test(piva)) return false;
        
        // Luhn algorithm for Italian VAT
        let sum = 0;
        for (let i = 0; i < 10; i++) {
            let digit = parseInt(piva[i]);
            if (i % 2 === 0) {
                digit *= 2;
                if (digit > 9) digit -= 9;
            }
            sum += digit;
        }
        
        const checkDigit = (10 - (sum % 10)) % 10;
        return checkDigit === parseInt(piva[10]);
    }
    
    validateEmail(email) {
        const pattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        return pattern.test(email);
    }
    
    // Tab system
    setupTabSystem() {
        const tabButtons = document.querySelectorAll('.tab-btn');
        const tabPanes = document.querySelectorAll('.tab-pane');
        
        tabButtons.forEach(btn => {
            btn.addEventListener('click', () => {
                const targetTab = btn.dataset.tab;
                
                // Check for unsaved changes before switching
                if (Object.keys(this.pendingChanges).length > 0) {
                    if (!confirm('Hai modifiche non salvate. Vuoi cambiar tab comunque?')) {
                        return;
                    }
                }
                
                // Update buttons
                tabButtons.forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                
                // Update panes with animation
                tabPanes.forEach(pane => {
                    if (pane.id === `tab-${targetTab}`) {
                        pane.style.display = 'block';
                        requestAnimationFrame(() => {
                            pane.classList.add('active', 'fade-in');
                        });
                    } else {
                        pane.classList.remove('active');
                        setTimeout(() => {
                            if (!pane.classList.contains('active')) {
                                pane.style.display = 'none';
                            }
                        }, 300);
                    }
                });
                
                // Save tab preference
                localStorage.setItem('activeTab', targetTab);
                
                // Lazy load tab content if needed
                this.loadTabContent(targetTab);
            });
        });
        
        // Restore last active tab
        const lastTab = localStorage.getItem('activeTab');
        if (lastTab) {
            const tabBtn = document.querySelector(`.tab-btn[data-tab="${lastTab}"]`);
            if (tabBtn) tabBtn.click();
        }
    }
    
    // Lazy load tab content
    async loadTabContent(tabName) {
        const tabPane = document.getElementById(`tab-${tabName}`);
        if (!tabPane || tabPane.dataset.loaded === 'true') return;
        
        // Mark as loaded
        tabPane.dataset.loaded = 'true';
        
        // Load specific content based on tab
        switch(tabName) {
            case 'formazione':
                await this.loadEducationData();
                break;
            case 'esperienza':
                await this.loadExperienceData();
                break;
            case 'ferie':
                await this.loadLeaveData();
                break;
            case 'retribuzione':
                await this.loadSalaryData();
                break;
        }
    }
    
    // Editable fields
    setupEditableFields() {
        if (!this.canEdit) return;
        
        document.querySelectorAll('.editable-field').forEach(field => {
            field.addEventListener('click', (e) => {
                if (field.classList.contains('editing')) return;
                
                const value = field.querySelector('.value').textContent.trim();
                const fieldName = field.dataset.field;
                const fieldType = field.dataset.type || 'text';
                
                field.classList.add('editing');
                field.dataset.originalValue = value;
                
                let input = this.createEditableInput(fieldType, value, field.dataset);
                
                field.innerHTML = '';
                field.appendChild(input);
                input.focus();
                
                if (input.select) input.select();
                
                const saveField = async () => {
                    const newValue = input.value;
                    
                    if (newValue !== value) {
                        await this.updateSingleField(fieldName, newValue, field);
                    } else {
                        this.restoreEditableField(field, value);
                    }
                };
                
                input.addEventListener('blur', saveField);
                input.addEventListener('keydown', (e) => {
                    if (e.key === 'Enter' && fieldType !== 'textarea') {
                        e.preventDefault();
                        saveField();
                    }
                    if (e.key === 'Escape') {
                        this.restoreEditableField(field, value);
                    }
                });
            });
        });
    }
    
    createEditableInput(type, value, dataset) {
        let input;
        
        switch(type) {
            case 'textarea':
                input = document.createElement('textarea');
                input.rows = dataset.rows || 3;
                break;
                
            case 'select':
                input = document.createElement('select');
                if (dataset.options) {
                    JSON.parse(dataset.options).forEach(opt => {
                        const option = document.createElement('option');
                        option.value = opt.value || opt;
                        option.text = opt.label || opt;
                        option.selected = (opt.value || opt) === value;
                        input.appendChild(option);
                    });
                }
                break;
                
            case 'date':
                input = document.createElement('input');
                input.type = 'date';
                // Convert display date to ISO format
                if (value && value !== '—') {
                    const parts = value.split('/');
                    if (parts.length === 3) {
                        input.value = `${parts[2]}-${parts[1]}-${parts[0]}`;
                    }
                }
                break;
                
            case 'number':
                input = document.createElement('input');
                input.type = 'number';
                input.step = dataset.step || '1';
                input.min = dataset.min || '';
                input.max = dataset.max || '';
                break;
                
            default:
                input = document.createElement('input');
                input.type = type;
        }
        
        if (input.tagName !== 'SELECT') {
            input.value = value === '—' ? '' : value;
        }
        
        input.className = 'form-input';
        return input;
    }
    
    async updateSingleField(fieldName, value, element) {
        this.updateSaveIndicator('saving');
        
        try {
            const response = await fetch(this.endpoints.updateField, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.csrfToken
                },
                body: JSON.stringify({
                    field: fieldName,
                    value: value
                })
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.updateSaveIndicator('saved');
                this.restoreEditableField(element, data.display_value || value || '—');
                this.showNotification('success', 'Campo aggiornato');
            } else {
                throw new Error(data.message || 'Update failed');
            }
        } catch (error) {
            this.updateSaveIndicator('error');
            this.showNotification('error', 'Errore durante l\'aggiornamento');
            this.restoreEditableField(element, element.dataset.originalValue || '—');
        }
    }
    
    restoreEditableField(element, value) {
        element.classList.remove('editing');
        element.innerHTML = `
            <span class="value">${value}</span>
            <i class="ri-pencil-line edit-icon"></i>
        `;
    }
    
    // File uploads
    setupFileUploads() {
        // Avatar upload
        const avatarInput = document.getElementById('avatarInput');
        if (avatarInput) {
            avatarInput.addEventListener('change', (e) => this.uploadAvatar(e.target.files[0]));
        }
        
        // Document uploads
        document.querySelectorAll('.document-upload').forEach(input => {
            input.addEventListener('change', (e) => {
                this.uploadDocument(e.target.files[0], input.dataset.docType);
            });
        });
    }
    
    async uploadAvatar(file) {
        if (!file) return;
        
        // Validate file
        if (!file.type.startsWith('image/')) {
            this.showNotification('error', 'Seleziona un file immagine valido');
            return;
        }
        
        if (file.size > 5 * 1024 * 1024) {
            this.showNotification('error', 'L\'immagine deve essere inferiore a 5MB');
            return;
        }
        
        const formData = new FormData();
        formData.append('avatar', file);
        
        this.updateSaveIndicator('saving');
        
        try {
            const response = await fetch(this.endpoints.uploadAvatar, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': this.csrfToken
                },
                body: formData
            });
            
            const data = await response.json();
            
            if (data.success) {
                document.getElementById('avatarImg').src = data.avatar_url + '?t=' + Date.now();
                this.updateSaveIndicator('saved');
                this.showNotification('success', 'Avatar aggiornato');
            } else {
                throw new Error(data.message);
            }
        } catch (error) {
            this.updateSaveIndicator('error');
            this.showNotification('error', 'Errore durante il caricamento');
        }
    }
    
    // Skills manager
    setupSkillsManager() {
        // Technical skills
        const addSkillBtn = document.getElementById('addTechnicalSkill');
        if (addSkillBtn) {
            addSkillBtn.addEventListener('click', () => this.addSkillModal('technical'));
        }
        
        // Soft skills
        const addSoftSkillBtn = document.getElementById('addSoftSkill');
        if (addSoftSkillBtn) {
            addSoftSkillBtn.addEventListener('click', () => this.addSkillModal('soft'));
        }
        
        // Language skills
        const addLanguageBtn = document.getElementById('addLanguage');
        if (addLanguageBtn) {
            addLanguageBtn.addEventListener('click', () => this.addLanguageModal());
        }
        
        // Skill level editors
        document.querySelectorAll('.skill-level').forEach(skillEl => {
            skillEl.addEventListener('click', () => this.editSkillLevel(skillEl));
        });
    }
    
    // Date pickers
    setupDatePickers() {
        flatpickr('.date-picker', {
            dateFormat: 'd/m/Y',
            locale: 'it',
            allowInput: true
        });
        
        flatpickr('.datetime-picker', {
            enableTime: true,
            dateFormat: 'd/m/Y H:i',
            locale: 'it',
            time_24hr: true
        });
        
        flatpickr('.date-range-picker', {
            mode: 'range',
            dateFormat: 'd/m/Y',
            locale: 'it'
        });
    }
    
    // Select2
    setupSelect2() {
        $('.select2').select2({
            theme: 'bootstrap-5',
            width: '100%',
            placeholder: 'Seleziona...',
            allowClear: true
        });
        
        $('.select2-tags').select2({
            theme: 'bootstrap-5',
            width: '100%',
            tags: true,
            tokenSeparators: [',', ' ']
        });
    }
    
    // Tooltips
    setupTooltips() {
        const tooltips = document.querySelectorAll('[data-tooltip]');
        tooltips.forEach(el => {
            el.setAttribute('title', el.dataset.tooltip);
            // Initialize your preferred tooltip library
        });
    }
    
    // UI Updates
    updateSaveIndicator(status) {
        const indicator = document.getElementById('saveIndicator');
        if (!indicator) return;
        
        indicator.className = `save-indicator ${status} show`;
        
        const spinner = indicator.querySelector('#saveSpinner');
        const text = indicator.querySelector('#saveText');
        
        switch(status) {
            case 'saving':
                if (spinner) spinner.style.display = 'inline-block';
                if (text) text.textContent = 'Salvataggio...';
                break;
            case 'saved':
                if (spinner) spinner.style.display = 'none';
                if (text) text.textContent = 'Salvato!';
                setTimeout(() => indicator.classList.remove('show'), 3000);
                break;
            case 'error':
                if (spinner) spinner.style.display = 'none';
                if (text) text.textContent = 'Errore!';
                setTimeout(() => indicator.classList.remove('show'), 3000);
                break;
            case 'pending':
                if (spinner) spinner.style.display = 'none';
                if (text) text.textContent = 'Modifiche non salvate';
                break;
        }
    }
    
    showNotification(type, message) {
        if (typeof toastr !== 'undefined') {
            toastr[type](message);
        } else {
            // Fallback notification
            const notification = document.createElement('div');
            notification.className = `alert alert-${type} notification-toast`;
            notification.textContent = message;
            document.body.appendChild(notification);
            
            setTimeout(() => {
                notification.classList.add('show');
            }, 100);
            
            setTimeout(() => {
                notification.classList.remove('show');
                setTimeout(() => notification.remove(), 300);
            }, 3000);
        }
    }
    
    // Data loading methods
    async loadEducationData() {
        // Load education data via AJAX if needed
    }
    
    async loadExperienceData() {
        // Load experience data via AJAX if needed
    }
    
    async loadLeaveData() {
        // Load leave/vacation data via AJAX if needed
    }
    
    async loadSalaryData() {
        // Load salary data via AJAX if needed (with permission check)
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    // Check if we're on the profile page
    const profileContainer = document.getElementById('profileEditor');
    if (profileContainer) {
        const config = {
            userId: profileContainer.dataset.userId,
            canEdit: profileContainer.dataset.canEdit === 'true',
            csrfToken: profileContainer.dataset.csrfToken
        };
        
        window.profileEditor = new TeamProfileEditor(config);
    }
});

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = TeamProfileEditor;
}
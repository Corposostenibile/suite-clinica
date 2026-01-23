/**
 * Form Builder - Conditional Logic System
 * Gestisce la logica condizionale per mostrare/nascondere domande
 */

class FormBuilderLogic {
    constructor() {
        this.questions = [];
        this.conditions = {};
        this.init();
    }

    init() {
        this.loadQuestions();
        this.attachEventListeners();
    }

    loadQuestions() {
        // Carica domande esistenti dal DOM
        document.querySelectorAll('.question-card').forEach(card => {
            const questionId = card.dataset.questionId;
            const questionText = card.querySelector('input[type="text"]').value;
            const questionType = card.querySelector('select.question-type').value;
            
            this.questions.push({
                id: questionId,
                text: questionText,
                type: questionType
            });
        });
    }

    attachEventListeners() {
        // Pulsante per aggiungere condizione
        document.addEventListener('click', (e) => {
            if (e.target.classList.contains('add-condition-btn')) {
                const questionId = e.target.dataset.questionId;
                this.showConditionModal(questionId);
            }
        });
    }

    showConditionModal(questionId) {
        const modal = this.createConditionModal(questionId);
        document.body.appendChild(modal);
        
        // Mostra modal con Bootstrap
        const bsModal = new bootstrap.Modal(modal);
        bsModal.show();
        
        // Rimuovi modal dopo chiusura
        modal.addEventListener('hidden.bs.modal', () => {
            modal.remove();
        });
    }

    createConditionModal(questionId) {
        const modal = document.createElement('div');
        modal.className = 'modal fade';
        modal.innerHTML = `
            <div class="modal-dialog modal-lg">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title">Logica Condizionale</h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body">
                        <div class="mb-3">
                            <label class="form-label">Mostra questa domanda quando:</label>
                        </div>
                        
                        <div id="conditions-container">
                            ${this.renderConditionBuilder(questionId)}
                        </div>
                        
                        <button class="btn btn-sm btn-outline-primary mt-3" onclick="formLogic.addConditionRule('${questionId}')">
                            <i class="bi bi-plus"></i> Aggiungi Condizione
                        </button>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Annulla</button>
                        <button type="button" class="btn btn-primary" onclick="formLogic.saveConditions('${questionId}')">
                            Salva Condizioni
                        </button>
                    </div>
                </div>
            </div>
        `;
        return modal;
    }

    renderConditionBuilder(questionId) {
        const existingConditions = this.conditions[questionId] || [];
        
        if (existingConditions.length === 0) {
            return this.renderConditionRule(questionId, 0);
        }
        
        return existingConditions.map((condition, index) => 
            this.renderConditionRule(questionId, index, condition)
        ).join('');
    }

    renderConditionRule(questionId, index, condition = {}) {
        const otherQuestions = this.questions.filter(q => q.id !== questionId);
        
        return `
            <div class="condition-rule card mb-2" data-index="${index}">
                <div class="card-body">
                    <div class="row g-2">
                        <div class="col-md-4">
                            <select class="form-select condition-question" data-question-id="${questionId}" data-index="${index}">
                                <option value="">Seleziona domanda...</option>
                                ${otherQuestions.map(q => `
                                    <option value="${q.id}" ${condition.questionId === q.id ? 'selected' : ''}>
                                        ${q.text}
                                    </option>
                                `).join('')}
                            </select>
                        </div>
                        <div class="col-md-3">
                            <select class="form-select condition-operator" data-index="${index}">
                                <option value="equals" ${condition.operator === 'equals' ? 'selected' : ''}>È uguale a</option>
                                <option value="not_equals" ${condition.operator === 'not_equals' ? 'selected' : ''}>È diverso da</option>
                                <option value="contains" ${condition.operator === 'contains' ? 'selected' : ''}>Contiene</option>
                                <option value="not_contains" ${condition.operator === 'not_contains' ? 'selected' : ''}>Non contiene</option>
                                <option value="greater_than" ${condition.operator === 'greater_than' ? 'selected' : ''}>Maggiore di</option>
                                <option value="less_than" ${condition.operator === 'less_than' ? 'selected' : ''}>Minore di</option>
                            </select>
                        </div>
                        <div class="col-md-4">
                            <input type="text" class="form-control condition-value" 
                                   placeholder="Valore..." 
                                   value="${condition.value || ''}"
                                   data-index="${index}">
                        </div>
                        <div class="col-md-1">
                            <button class="btn btn-sm btn-danger" onclick="formLogic.removeConditionRule(${index})">
                                <i class="bi bi-trash"></i>
                            </button>
                        </div>
                    </div>
                    
                    ${index > 0 ? `
                        <div class="mt-2">
                            <div class="form-check form-check-inline">
                                <input class="form-check-input" type="radio" 
                                       name="logic-operator-${questionId}" 
                                       value="AND" 
                                       ${condition.logicOperator === 'AND' ? 'checked' : ''}>
                                <label class="form-check-label">E (AND)</label>
                            </div>
                            <div class="form-check form-check-inline">
                                <input class="form-check-input" type="radio" 
                                       name="logic-operator-${questionId}" 
                                       value="OR"
                                       ${condition.logicOperator === 'OR' ? 'checked' : ''}>
                                <label class="form-check-label">O (OR)</label>
                            </div>
                        </div>
                    ` : ''}
                </div>
            </div>
        `;
    }

    addConditionRule(questionId) {
        const container = document.getElementById('conditions-container');
        const index = container.children.length;
        const newRule = this.renderConditionRule(questionId, index);
        
        container.insertAdjacentHTML('beforeend', newRule);
    }

    removeConditionRule(index) {
        const rule = document.querySelector(`.condition-rule[data-index="${index}"]`);
        if (rule) {
            rule.remove();
        }
    }

    saveConditions(questionId) {
        const conditions = [];
        
        document.querySelectorAll('.condition-rule').forEach((rule, index) => {
            const questionSelect = rule.querySelector('.condition-question');
            const operatorSelect = rule.querySelector('.condition-operator');
            const valueInput = rule.querySelector('.condition-value');
            const logicRadio = rule.querySelector(`input[name="logic-operator-${questionId}"]:checked`);
            
            if (questionSelect.value) {
                conditions.push({
                    questionId: questionSelect.value,
                    operator: operatorSelect.value,
                    value: valueInput.value,
                    logicOperator: logicRadio ? logicRadio.value : 'AND'
                });
            }
        });
        
        this.conditions[questionId] = conditions;
        
        // Aggiorna UI per mostrare che ci sono condizioni
        this.updateConditionIndicator(questionId, conditions.length > 0);
        
        // Chiudi modal
        const modal = bootstrap.Modal.getInstance(document.querySelector('.modal'));
        if (modal) {
            modal.hide();
        }
        
        // Salva sul server
        this.syncConditionsToServer();
    }

    updateConditionIndicator(questionId, hasConditions) {
        const card = document.querySelector(`.question-card[data-question-id="${questionId}"]`);
        if (!card) return;
        
        let indicator = card.querySelector('.condition-indicator');
        
        if (hasConditions) {
            if (!indicator) {
                indicator = document.createElement('span');
                indicator.className = 'condition-indicator badge bg-info ms-2';
                indicator.innerHTML = '<i class="bi bi-filter"></i> Con Condizioni';
                card.querySelector('.card-title').appendChild(indicator);
            }
        } else {
            if (indicator) {
                indicator.remove();
            }
        }
    }

    syncConditionsToServer() {
        // Prepara dati per invio al server
        const formData = {
            conditions: this.conditions,
            questions: this.questions
        };
        
        // Qui andrebbe la chiamata AJAX per salvare sul server
        console.log('Saving conditions:', formData);
    }

    // Metodo per applicare le condizioni in runtime (quando il form viene compilato)
    applyConditions(formAnswers) {
        const visibleQuestions = new Set();
        
        // Prima, mostra tutte le domande senza condizioni
        this.questions.forEach(q => {
            if (!this.conditions[q.id] || this.conditions[q.id].length === 0) {
                visibleQuestions.add(q.id);
            }
        });
        
        // Poi, valuta le condizioni
        for (const [questionId, conditions] of Object.entries(this.conditions)) {
            const shouldShow = this.evaluateConditions(conditions, formAnswers);
            if (shouldShow) {
                visibleQuestions.add(questionId);
            }
        }
        
        return visibleQuestions;
    }

    evaluateConditions(conditions, formAnswers) {
        if (conditions.length === 0) return true;
        
        let result = this.evaluateCondition(conditions[0], formAnswers);
        
        for (let i = 1; i < conditions.length; i++) {
            const condition = conditions[i];
            const conditionResult = this.evaluateCondition(condition, formAnswers);
            
            if (condition.logicOperator === 'AND') {
                result = result && conditionResult;
            } else {
                result = result || conditionResult;
            }
        }
        
        return result;
    }

    evaluateCondition(condition, formAnswers) {
        const answer = formAnswers[condition.questionId];
        const expectedValue = condition.value;
        
        switch (condition.operator) {
            case 'equals':
                return answer == expectedValue;
            case 'not_equals':
                return answer != expectedValue;
            case 'contains':
                return answer && answer.toString().includes(expectedValue);
            case 'not_contains':
                return !answer || !answer.toString().includes(expectedValue);
            case 'greater_than':
                return parseFloat(answer) > parseFloat(expectedValue);
            case 'less_than':
                return parseFloat(answer) < parseFloat(expectedValue);
            default:
                return false;
        }
    }
}

// Inizializza quando il DOM è pronto
document.addEventListener('DOMContentLoaded', () => {
    window.formLogic = new FormBuilderLogic();
});
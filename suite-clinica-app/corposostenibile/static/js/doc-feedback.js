// Sistema di feedback per la documentazione
$(document).ready(function() {
    
    // Funzione per ottenere i cookie
    function getCookie(name) {
        var cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            var cookies = document.cookie.split(';');
            for (var i = 0; i < cookies.length; i++) {
                var cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }
    
    // Setup AJAX con CSRF token
    $.ajaxSetup({
        beforeSend: function(xhr, settings) {
            if (!/^(GET|HEAD|OPTIONS|TRACE)$/i.test(settings.type) && !this.crossDomain) {
                // Usa il token globale se disponibile
                if (window.CSRF_TOKEN) {
                    xhr.setRequestHeader("X-CSRFToken", window.CSRF_TOKEN);
                }
            }
        }
    });
    
    // Gestione click feedback positivo
    $(document).on('click', '.feedback-positive', function(e) {
        e.preventDefault();
        var $button = $(this);
        var page = window.location.pathname;
        var module = getModuleName();
        
        // Invia feedback positivo
        $.ajax({
            url: '/help/feedback',
            method: 'POST',
            data: {
                type: 'positive',
                page: page,
                module: module
            },
            success: function(response) {
                // Mostra messaggio di ringraziamento
                showFeedbackMessage($button.closest('.doc-feedback'), 'positive', 'Grazie del tuo prezioso feedback! 👍');
            },
            error: function(xhr, status, error) {
                console.error('Errore feedback positivo:', status, error, xhr.responseText);
                showFeedbackMessage($button.closest('.doc-feedback'), 'error', 'Errore nell\'invio del feedback. Riprova.');
            }
        });
    });
    
    // Gestione click feedback negativo - apre modal
    $(document).on('click', '.feedback-negative', function(e) {
        e.preventDefault();
        var page = window.location.pathname;
        var module = getModuleName();
        
        // Mostra modal per feedback dettagliato
        showFeedbackModal(page, module);
    });
    
    // Funzione per mostrare il modal di feedback negativo
    function showFeedbackModal(page, module) {
        // Rimuovi modal esistente se presente
        $('#feedbackModal').remove();
        
        var modalHtml = `
            <div class="modal fade" id="feedbackModal" tabindex="-1" role="dialog">
                <div class="modal-dialog" role="document">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title">Aiutaci a migliorare la documentazione</h5>
                            <button type="button" class="close" data-dismiss="modal">
                                <span>&times;</span>
                            </button>
                        </div>
                        <div class="modal-body">
                            <p>Ci dispiace che la documentazione non ti sia stata utile. Il tuo feedback è importante per migliorare.</p>
                            
                            <form id="feedbackForm">
                                <div class="form-group">
                                    <label>Cosa non hai trovato utile?</label>
                                    <textarea class="form-control" id="feedbackProblem" rows="3" 
                                        placeholder="Es: Le spiegazioni non sono chiare, mancano esempi pratici..." required></textarea>
                                </div>
                                
                                <div class="form-group">
                                    <label>Cosa ti aspettavi di trovare?</label>
                                    <textarea class="form-control" id="feedbackExpectation" rows="3" 
                                        placeholder="Es: Più esempi, screenshot delle schermate, casi d'uso specifici..." required></textarea>
                                </div>
                                
                                <div class="form-group">
                                    <label>Suggerimenti per migliorare (opzionale)</label>
                                    <textarea class="form-control" id="feedbackSuggestions" rows="2" 
                                        placeholder="Altre idee o suggerimenti..."></textarea>
                                </div>
                                
                                <input type="hidden" id="feedbackPage" value="${page}">
                                <input type="hidden" id="feedbackModule" value="${module}">
                            </form>
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" data-dismiss="modal">Annulla</button>
                            <button type="button" class="btn btn-primary" id="submitFeedback">Invia Feedback</button>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        $('body').append(modalHtml);
        $('#feedbackModal').modal('show');
        
        // Gestione invio form
        $('#submitFeedback').click(function() {
            var problem = $('#feedbackProblem').val().trim();
            var expectation = $('#feedbackExpectation').val().trim();
            var suggestions = $('#feedbackSuggestions').val().trim();
            
            if (!problem || !expectation) {
                alert('Per favore compila i campi obbligatori');
                return;
            }
            
            // Disabilita pulsante durante invio
            $(this).prop('disabled', true).text('Invio in corso...');
            
            // Invia feedback
            $.ajax({
                url: '/help/feedback',
                method: 'POST',
                data: {
                    type: 'negative',
                    page: page,
                    module: module,
                    problem: problem,
                    expectation: expectation,
                    suggestions: suggestions
                },
                success: function(response) {
                    $('#feedbackModal').modal('hide');
                    // Mostra messaggio di conferma
                    showFeedbackMessage($('.doc-feedback'), 'positive', 
                        'Grazie per il tuo feedback dettagliato! Lo useremo per migliorare la documentazione.');
                },
                error: function(xhr, status, error) {
                    console.error('Errore feedback negativo:', status, error, xhr.responseText);
                    alert('Errore nell\'invio del feedback. Riprova più tardi.\n\nDettagli: ' + (xhr.responseJSON ? xhr.responseJSON.error : error));
                    $('#submitFeedback').prop('disabled', false).text('Invia Feedback');
                }
            });
        });
    }
    
    // Funzione per mostrare messaggi di feedback
    function showFeedbackMessage(container, type, message) {
        var alertClass = type === 'positive' ? 'alert-success' : 'alert-danger';
        var messageHtml = `
            <div class="alert ${alertClass} alert-dismissible fade show mt-3" role="alert">
                ${message}
                <button type="button" class="close" data-dismiss="alert">
                    <span>&times;</span>
                </button>
            </div>
        `;
        
        // Sostituisci i pulsanti con il messaggio
        container.html(messageHtml);
    }
    
    // Funzione per ottenere il nome del modulo dalla pagina
    function getModuleName() {
        var path = window.location.pathname;
        if (path.includes('ticket')) return 'Ticketing';
        if (path.includes('communications')) return 'Comunicazioni';
        if (path.includes('training')) return 'Training';
        if (path.includes('clienti')) return 'Clienti';
        if (path.includes('check')) return 'Check';
        if (path.includes('documentation-suite')) return 'Dashboard';
        return 'Generale';
    }
});
/**
 * JavaScript per il sistema di chat delle Review/Training
 */

document.addEventListener('DOMContentLoaded', function() {
    
    // Auto-scroll all'ultimo messaggio in tutte le chat
    const chatContainers = document.querySelectorAll('.chat-messages');
    chatContainers.forEach(container => {
        container.scrollTop = container.scrollHeight;
    });
    
    // Gestione form invio messaggio con validazione
    const messageForms = document.querySelectorAll('form[action*="/review/message/"]');
    messageForms.forEach(form => {
        form.addEventListener('submit', function(e) {
            const textarea = form.querySelector('textarea[name="content"]');
            if (!textarea.value.trim()) {
                e.preventDefault();
                alert('Il messaggio non può essere vuoto!');
                textarea.focus();
                return false;
            }
            
            // Disabilita il bottone di invio per evitare doppi invii
            const submitBtn = form.querySelector('button[type="submit"]');
            if (submitBtn) {
                submitBtn.disabled = true;
                submitBtn.innerHTML = '<i class="ri-loader-4-line ri-spin"></i> Invio in corso...';
            }
        });
    });
    
    // Gestione bottoni "Segna come letto" con conferma visuale
    const readButtons = document.querySelectorAll('form[action*="/message/"][action*="/read"]');
    readButtons.forEach(form => {
        form.addEventListener('submit', function(e) {
            const submitBtn = form.querySelector('button[type="submit"]');
            if (submitBtn) {
                submitBtn.disabled = true;
                submitBtn.innerHTML = '<i class="ri-check-double-line"></i> Letto';
                submitBtn.classList.remove('btn-outline-primary');
                submitBtn.classList.add('btn-success');
            }
        });
    });
    
    // Auto-resize textarea quando si scrive
    const messageTextareas = document.querySelectorAll('.new-message-form textarea');
    messageTextareas.forEach(textarea => {
        // Imposta altezza iniziale
        textarea.style.minHeight = '60px';
        textarea.style.maxHeight = '200px';
        
        // Auto-resize on input
        textarea.addEventListener('input', function() {
            this.style.height = 'auto';
            this.style.height = Math.min(this.scrollHeight, 200) + 'px';
        });
        
        // Gestione Ctrl+Enter per invio rapido
        textarea.addEventListener('keydown', function(e) {
            if (e.ctrlKey && e.key === 'Enter') {
                e.preventDefault();
                const form = this.closest('form');
                if (form) {
                    form.requestSubmit();
                }
            }
        });
    });
    
    // Badge animato per messaggi non letti
    const unreadBadges = document.querySelectorAll('.badge:contains("da leggere")');
    unreadBadges.forEach(badge => {
        badge.classList.add('pulse-animation');
    });
    
    // Notifica sonora per nuovi messaggi (se abilitata)
    if (window.localStorage.getItem('review_chat_sound') !== 'disabled') {
        const unreadCount = document.querySelectorAll('.message-item form[action*="/read"]').length;
        if (unreadCount > 0 && window.Audio) {
            // Crea un suono di notifica semplice
            const audio = new Audio('data:audio/wav;base64,UklGRnoGAABXQVZFZm10IBAAAAABAAEARKwAAIhYAQACABAAZGF0YQoGAAA=');
            audio.volume = 0.3;
            // audio.play().catch(() => {}); // Commentato per non disturbare, può essere abilitato
        }
    }
    
    // Aggiorna contatore nel titolo della pagina
    function updatePageTitle() {
        const originalTitle = document.title.replace(/^\(\d+\)\s*/, '');
        const totalUnread = document.querySelectorAll('.badge:contains("da leggere")').length;
        
        if (totalUnread > 0) {
            document.title = `(${totalUnread}) ${originalTitle}`;
        } else {
            document.title = originalTitle;
        }
    }
    
    updatePageTitle();
    
    // Mostra/nascondi area chat con animazione
    const chatCards = document.querySelectorAll('[id^="review-"][id$="-chat"]');
    chatCards.forEach(card => {
        const header = card.querySelector('.card-header');
        if (header) {
            header.style.cursor = 'pointer';
            header.addEventListener('click', function(e) {
                // Non collassare se si clicca su un bottone
                if (e.target.closest('button, form')) return;
                
                const body = card.querySelector('.card-body');
                if (body) {
                    if (body.style.display === 'none') {
                        body.style.display = 'block';
                        // Scroll to chat
                        card.scrollIntoView({ behavior: 'smooth', block: 'center' });
                    } else {
                        body.style.display = 'none';
                    }
                }
            });
        }
    });
    
    // Timestamp relativi (es. "2 ore fa")
    function updateRelativeTime() {
        const timeElements = document.querySelectorAll('.message-item small:contains("/")');
        timeElements.forEach(elem => {
            const text = elem.textContent;
            const dateMatch = text.match(/(\d{2})\/(\d{2})\/(\d{4})\s+(\d{2}):(\d{2})/);
            if (dateMatch) {
                const [_, day, month, year, hour, minute] = dateMatch;
                const messageDate = new Date(year, month - 1, day, hour, minute);
                const now = new Date();
                const diffMs = now - messageDate;
                const diffMins = Math.floor(diffMs / 60000);
                
                let relativeTime = '';
                if (diffMins < 1) {
                    relativeTime = 'ora';
                } else if (diffMins < 60) {
                    relativeTime = `${diffMins} ${diffMins === 1 ? 'minuto' : 'minuti'} fa`;
                } else if (diffMins < 1440) {
                    const hours = Math.floor(diffMins / 60);
                    relativeTime = `${hours} ${hours === 1 ? 'ora' : 'ore'} fa`;
                } else if (diffMins < 10080) {
                    const days = Math.floor(diffMins / 1440);
                    relativeTime = `${days} ${days === 1 ? 'giorno' : 'giorni'} fa`;
                }
                
                if (relativeTime && elem.title !== text) {
                    elem.title = text; // Mostra data completa al hover
                    elem.textContent = relativeTime;
                }
            }
        });
    }
    
    // Aggiorna ogni minuto
    updateRelativeTime();
    setInterval(updateRelativeTime, 60000);
    
    // Focus automatico sul campo messaggio quando si apre la chat
    document.addEventListener('click', function(e) {
        if (e.target.matches('a[href*="#review-"][href*="-chat"]')) {
            setTimeout(() => {
                const chatId = e.target.getAttribute('href').substring(1);
                const textarea = document.querySelector(`#${chatId} textarea[name="content"]`);
                if (textarea) {
                    textarea.focus();
                }
            }, 300);
        }
    });
    
});

// CSS per animazione pulse
const style = document.createElement('style');
style.textContent = `
    .pulse-animation {
        animation: pulse 2s infinite;
    }
    
    @keyframes pulse {
        0% {
            transform: scale(1);
            opacity: 1;
        }
        50% {
            transform: scale(1.1);
            opacity: 0.8;
        }
        100% {
            transform: scale(1);
            opacity: 1;
        }
    }
    
    .ri-spin {
        animation: spin 1s linear infinite;
    }
    
    @keyframes spin {
        from {
            transform: rotate(0deg);
        }
        to {
            transform: rotate(360deg);
        }
    }
    
    .chat-messages {
        border: 1px solid #e5e7eb;
        border-radius: 8px;
        padding: 15px;
        background: #f9fafb;
    }
    
    .message-item {
        animation: fadeIn 0.3s ease-in;
    }
    
    @keyframes fadeIn {
        from {
            opacity: 0;
            transform: translateY(10px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }
`;
document.head.appendChild(style);
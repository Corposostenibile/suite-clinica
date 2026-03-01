import { useState, useRef, useEffect } from 'react';
import sopService from '../../services/sopService';

export default function SOPChat() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [sessionId, setSessionId] = useState(null);
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  const handleSend = async () => {
    const query = input.trim();
    if (!query || loading) return;

    setInput('');
    setMessages((prev) => [...prev, { role: 'user', content: query }]);
    setLoading(true);

    try {
      const data = await sopService.chat(query, sessionId);
      if (data.session_id) setSessionId(data.session_id);
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: data.response,
          sources: data.sources || [],
        },
      ]);
    } catch {
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: 'Si è verificato un errore. Riprova tra qualche istante.',
          sources: [],
        },
      ]);
    } finally {
      setLoading(false);
      inputRef.current?.focus();
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleNewConversation = async () => {
    if (sessionId) {
      try {
        await sopService.clearChat(sessionId);
      } catch { /* ignore */ }
    }
    setMessages([]);
    setSessionId(null);
    inputRef.current?.focus();
  };

  return (
    <div className="container-fluid">
      <div className="row page-titles">
        <ol className="breadcrumb">
          <li className="breadcrumb-item"><a href="#">SOP Chatbot</a></li>
          <li className="breadcrumb-item active">Chat Test</li>
        </ol>
      </div>

      <div className="row">
        <div className="col-12">
          <div className="card" style={{ height: 'calc(100vh - 200px)', display: 'flex', flexDirection: 'column' }}>
            {/* Header */}
            <div className="card-header d-flex justify-content-between align-items-center">
              <h4 className="card-title mb-0">
                <i className="fas fa-robot me-2"></i>
                SOP Chatbot - Test
              </h4>
              <button
                className="btn btn-outline-secondary btn-sm"
                onClick={handleNewConversation}
              >
                <i className="fas fa-plus me-1"></i>
                Nuova conversazione
              </button>
            </div>

            {/* Messages area */}
            <div className="card-body" style={{ flex: 1, overflowY: 'auto', padding: '1rem' }}>
              {messages.length === 0 && (
                <div className="text-center text-muted py-5">
                  <i className="fas fa-comments fa-3x mb-3"></i>
                  <p>Fai una domanda sui documenti SOP aziendali</p>
                  <small>Le risposte saranno basate esclusivamente sui documenti caricati</small>
                </div>
              )}

              {messages.map((msg, i) => (
                <div
                  key={i}
                  className={`d-flex mb-3 ${msg.role === 'user' ? 'justify-content-end' : 'justify-content-start'}`}
                >
                  <div
                    style={{
                      maxWidth: '75%',
                      padding: '0.75rem 1rem',
                      borderRadius: msg.role === 'user' ? '1rem 1rem 0 1rem' : '1rem 1rem 1rem 0',
                      backgroundColor: msg.role === 'user' ? '#4CAF50' : '#f1f1f1',
                      color: msg.role === 'user' ? '#fff' : '#333',
                    }}
                  >
                    <div style={{ whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>
                      {msg.content}
                    </div>
                    {msg.sources && msg.sources.length > 0 && (
                      <div className="mt-2 pt-2" style={{ borderTop: '1px solid rgba(0,0,0,0.1)', fontSize: '0.8rem' }}>
                        <strong>Fonti:</strong>
                        {msg.sources.map((src, j) => (
                          <span key={j} className="badge bg-light text-dark ms-1">{src}</span>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              ))}

              {loading && (
                <div className="d-flex justify-content-start mb-3">
                  <div
                    style={{
                      padding: '0.75rem 1rem',
                      borderRadius: '1rem 1rem 1rem 0',
                      backgroundColor: '#f1f1f1',
                    }}
                  >
                    <div className="d-flex align-items-center">
                      <div className="spinner-border spinner-border-sm me-2" role="status" />
                      <span className="text-muted">Sta scrivendo...</span>
                    </div>
                  </div>
                </div>
              )}

              <div ref={messagesEndRef} />
            </div>

            {/* Input area */}
            <div className="card-footer" style={{ padding: '0.75rem 1rem' }}>
              <div className="input-group">
                <textarea
                  ref={inputRef}
                  className="form-control"
                  placeholder="Scrivi una domanda sui documenti SOP..."
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={handleKeyDown}
                  disabled={loading}
                  rows={1}
                  style={{ resize: 'none', borderRadius: '0.5rem 0 0 0.5rem' }}
                />
                <button
                  className="btn btn-primary"
                  onClick={handleSend}
                  disabled={!input.trim() || loading}
                  style={{ borderRadius: '0 0.5rem 0.5rem 0' }}
                >
                  <i className="fas fa-paper-plane"></i>
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

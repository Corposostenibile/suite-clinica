import React, { useState, useEffect, useCallback, useRef } from "react";
import { Link } from "react-router-dom";
import postitService, { POSTIT_COLORS, isPostitWrongEntrypointError } from "../../services/postitService";
import taskService, { TASK_PRIORITIES, TASK_CATEGORIES } from "../../services/taskService";
import './ChatBox.css';

const TABS = [
   { key: "chat", label: "Chat", icon: "ri-chat-3-line" },
   { key: "postit", label: "Post-it", icon: "ri-sticky-note-line" },
   { key: "task", label: "Task", icon: "ri-task-line" },
];

const ChatBox = ({ onClick, toggle }) => {
   const [activeTab, setActiveTab] = useState("chat");

   // Post-it state
   const [postits, setPostits] = useState([]);
   const [loading, setLoading] = useState(false);
   const [showCreateForm, setShowCreateForm] = useState(false);
   const [editingPostit, setEditingPostit] = useState(null);
   const [formData, setFormData] = useState({ content: '', color: 'yellow' });
   const [actionLoading, setActionLoading] = useState(false);
   const loadingPostitsRef = useRef(false);

   // Task state
   const [tasks, setTasks] = useState([]);
   const [loadingTasks, setLoadingTasks] = useState(false);
   const loadingTasksRef = useRef(false);

   // Task modal
   const [selectedTask, setSelectedTask] = useState(null);

   const postitWrongEntrypointMessage = 'I post-it non sono disponibili su questo endpoint. Apri la Suite dall\'indirizzo corretto della clinica.';

   // ── Post-it logic ──
   const loadPostits = useCallback(async () => {
      if (loadingPostitsRef.current) return;
      loadingPostitsRef.current = true;
      setLoading(true);
      try {
         const res = await postitService.getAll();
         setPostits(res.postits || []);
      } catch (err) {
         console.error('Errore caricamento post-it:', err);
         if (isPostitWrongEntrypointError(err)) alert(postitWrongEntrypointMessage);
      } finally {
         setLoading(false);
         loadingPostitsRef.current = false;
      }
   }, []);

   useEffect(() => {
      if (activeTab === 'postit' && toggle === 'chatbox') loadPostits();
   }, [activeTab, toggle, loadPostits]);

   const handleCreate = async (e) => {
      e.preventDefault();
      if (!formData.content.trim() || actionLoading) return;
      setActionLoading(true);
      try {
         const res = await postitService.create(formData);
         if (res.success) {
            setPostits(prev => [res.postit, ...prev]);
            setFormData({ content: '', color: 'yellow' });
            setShowCreateForm(false);
            await loadPostits();
         }
      } catch (err) {
         console.error('Errore creazione post-it:', err);
         if (isPostitWrongEntrypointError(err)) alert(postitWrongEntrypointMessage);
         else alert(err.response?.data?.error || err.message || 'Errore nella creazione del post-it');
      } finally { setActionLoading(false); }
   };

   const handleUpdate = async (e) => {
      e.preventDefault();
      if (!formData.content.trim() || actionLoading || !editingPostit) return;
      setActionLoading(true);
      try {
         const res = await postitService.update(editingPostit.id, formData);
         if (res.success) {
            setPostits(prev => prev.map(p => p.id === editingPostit.id ? res.postit : p));
            setFormData({ content: '', color: 'yellow' });
            setEditingPostit(null);
         }
      } catch (err) {
         console.error('Errore aggiornamento post-it:', err);
         alert('Errore nell\'aggiornamento del post-it');
      } finally { setActionLoading(false); }
   };

   const handleDelete = async (id) => {
      if (actionLoading) return;
      if (!window.confirm('Eliminare questo post-it?')) return;
      setActionLoading(true);
      try {
         const res = await postitService.delete(id);
         if (res.success) setPostits(prev => prev.filter(p => p.id !== id));
      } catch (err) {
         console.error('Errore eliminazione post-it:', err);
         alert('Errore nell\'eliminazione del post-it');
      } finally { setActionLoading(false); }
   };

   const startEdit = (postit) => {
      setEditingPostit(postit);
      setFormData({ content: postit.content, color: postit.color });
      setShowCreateForm(false);
   };

   const cancelForm = () => {
      setEditingPostit(null);
      setShowCreateForm(false);
      setFormData({ content: '', color: 'yellow' });
   };

   // ── Task logic ──
   const loadTasks = useCallback(async () => {
      if (loadingTasksRef.current) return;
      loadingTasksRef.current = true;
      setLoadingTasks(true);
      try {
         const res = await taskService.getAll({ completed: 'false', per_page: 20, mine: 'true' });
         setTasks(res || []);
      } catch (err) { console.error('Errore caricamento tasks:', err); }
      finally { setLoadingTasks(false); loadingTasksRef.current = false; }
   }, []);

   useEffect(() => {
      if (activeTab === 'task' && toggle === 'chatbox') loadTasks();
   }, [activeTab, toggle, loadTasks]);

   const toggleTaskCompletion = async (taskId, currentStatus) => {
      setTasks(prev => prev.filter(t => t.id !== taskId));
      try { await taskService.toggleComplete(taskId, !currentStatus); }
      catch (err) { console.error("Error updating task:", err); loadTasks(); }
   };

   const handleModalToggle = async () => {
      if (!selectedTask) return;
      try { await taskService.toggleComplete(selectedTask.id, !selectedTask.completed); }
      catch (e) { console.error(e); }
      setSelectedTask(null);
      loadTasks();
   };

   // ── Helpers ──
   const formatDate = (dateStr) => {
      if (!dateStr) return '';
      const date = new Date(dateStr);
      const today = new Date();
      const yesterday = new Date(today);
      yesterday.setDate(yesterday.getDate() - 1);
      if (date.toDateString() === today.toDateString()) return 'Oggi';
      if (date.toDateString() === yesterday.toDateString()) return 'Ieri';
      return date.toLocaleDateString('it-IT', { day: 'numeric', month: 'short' });
   };

   const getCategoryBadgeStyle = (catKey) => {
      const colors = {
         onboarding: { bg: '#e0f7fa', color: '#00838f', border: '#b2ebf2' },
         check:      { bg: '#e8f5e9', color: '#2e7d32', border: '#c8e6c9' },
         reminder:   { bg: '#fff8e1', color: '#e65100', border: '#ffecb3' },
         formazione: { bg: '#ede7f6', color: '#5e35b1', border: '#d1c4e9' },
         sollecito:  { bg: '#fce4ec', color: '#c62828', border: '#f8bbd0' },
         generico:   { bg: '#f5f5f5', color: '#616161', border: '#e0e0e0' },
      };
      return colors[catKey] || colors.generico;
   };

   return (
      <div className={`chatbox ${toggle === "chatbox" ? "active" : ""}`}>
         <div className="chatbox-close" onClick={() => onClick()}></div>
         <div className="d-flex flex-column h-100" style={{ background: 'white' }}>
            {/* Tabs */}
            <div className="cb-tab-header">
               {TABS.map((tab) => (
                  <button
                     key={tab.key}
                     className={`cb-tab-btn${activeTab === tab.key ? ' active' : ''}`}
                     onClick={() => setActiveTab(tab.key)}
                  >
                     <i className={tab.icon}></i>
                     {tab.label}
                  </button>
               ))}
            </div>

            <div className="cb-tab-content">
               {/* ═══ CHAT TAB ═══ */}
               <div className={`cb-tab-pane${activeTab === "chat" ? " active" : ""}`}>
                  <div className="cb-coming-soon">
                     <div className="cb-coming-icon">
                        <i className="ri-chat-3-line"></i>
                     </div>
                     <h6>Chat con i Pazienti</h6>
                     <p>Questa funzionalità sarà disponibile con l'uscita dell'app pazienti.</p>
                     <div className="cb-coming-badge">
                        <i className="ri-time-line"></i> Prossimamente
                     </div>
                  </div>
               </div>

               {/* ═══ POST-IT TAB ═══ */}
               <div className={`cb-tab-pane${activeTab === "postit" ? " active" : ""}`}>
                  <div className="cb-section-header">
                     <div className="cb-section-header-left">
                        <div className="cb-section-icon" style={{ background: 'linear-gradient(135deg, #eab308, #ca8a04)' }}>
                           <i className="ri-sticky-note-line"></i>
                        </div>
                        <div>
                           <div className="cb-section-title">Post-it</div>
                           <div className="cb-section-subtitle">{postits.length} promemoria</div>
                        </div>
                     </div>
                     <div style={{ display: 'flex', gap: '4px' }}>
                        <button
                           className={`cb-icon-btn${showCreateForm ? ' active' : ''}`}
                           onClick={() => { setShowCreateForm(true); setEditingPostit(null); setFormData({ content: '', color: 'yellow' }); }}
                           title="Nuovo post-it"
                        >
                           <i className="ri-add-line"></i>
                        </button>
                        <button className="cb-icon-btn" onClick={loadPostits} title="Aggiorna">
                           <i className={`ri-refresh-line${loading ? ' cb-spin' : ''}`}></i>
                        </button>
                     </div>
                  </div>

                  <div className="cb-scroll-body">
                     {/* Create/Edit Form */}
                     {(showCreateForm || editingPostit) && (
                        <div className="cb-postit-form">
                           <form onSubmit={editingPostit ? handleUpdate : handleCreate}>
                              <textarea
                                 className="cb-postit-textarea"
                                 value={formData.content}
                                 onChange={(e) => setFormData({ ...formData, content: e.target.value })}
                                 placeholder="Scrivi il tuo promemoria..."
                                 rows={3}
                                 style={{ background: POSTIT_COLORS[formData.color]?.bg || '#fff9c4' }}
                                 autoFocus
                              />
                              <div className="cb-color-picker">
                                 {Object.entries(POSTIT_COLORS).map(([key, val]) => (
                                    <button
                                       key={key}
                                       type="button"
                                       className={`cb-color-dot${formData.color === key ? ' selected' : ''}`}
                                       style={{ background: val.bg, borderColor: formData.color === key ? val.border : 'transparent' }}
                                       onClick={() => setFormData({ ...formData, color: key })}
                                       title={val.label}
                                    />
                                 ))}
                              </div>
                              <div className="cb-form-actions">
                                 <button type="submit" className="cb-btn-save" disabled={!formData.content.trim() || actionLoading}>
                                    {actionLoading ? <i className="ri-loader-4-line cb-spin"></i> : editingPostit ? (
                                       <><i className="ri-check-line"></i> Salva</>
                                    ) : (
                                       <><i className="ri-add-line"></i> Crea</>
                                    )}
                                 </button>
                                 <button type="button" className="cb-btn-cancel" onClick={cancelForm}>
                                    <i className="ri-close-line"></i>
                                 </button>
                              </div>
                           </form>
                        </div>
                     )}

                     {/* Post-it List */}
                     {loading && postits.length === 0 ? (
                        <div className="cb-loading">
                           <div className="cb-spinner"></div>
                           <p>Caricamento...</p>
                        </div>
                     ) : postits.length === 0 ? (
                        <div className="cb-empty">
                           <div className="cb-empty-icon">
                              <i className="ri-sticky-note-line"></i>
                           </div>
                           <h6>Nessun post-it</h6>
                           <p>Crea il tuo primo promemoria</p>
                           <button className="cb-empty-btn" onClick={() => setShowCreateForm(true)}>
                              <i className="ri-add-line"></i> Crea il primo
                           </button>
                        </div>
                     ) : (
                        <ul className="cb-postit-list">
                           {postits.map((postit) => (
                              <li
                                 key={postit.id}
                                 className="cb-postit-item"
                                 style={{
                                    background: POSTIT_COLORS[postit.color]?.bg || '#fff9c4'
                                 }}
                              >
                                 <div className="cb-postit-content">{postit.content}</div>
                                 <div className="cb-postit-meta">
                                    <span className="cb-postit-date">{formatDate(postit.createdAt)}</span>
                                    <div className="cb-postit-actions">
                                       <button className="cb-postit-action-btn edit" onClick={() => startEdit(postit)} title="Modifica">
                                          <i className="ri-pencil-line"></i>
                                       </button>
                                       <button className="cb-postit-action-btn delete" onClick={() => handleDelete(postit.id)} title="Elimina">
                                          <i className="ri-delete-bin-line"></i>
                                       </button>
                                    </div>
                                 </div>
                              </li>
                           ))}
                        </ul>
                     )}
                  </div>
               </div>

               {/* ═══ TASK TAB ═══ */}
               <div className={`cb-tab-pane${activeTab === "task" ? " active" : ""}`}>
                  <div className="cb-section-header">
                     <div className="cb-section-header-left">
                        <div className="cb-section-icon" style={{ background: 'linear-gradient(135deg, #f59e0b, #d97706)' }}>
                           <i className="ri-task-line"></i>
                        </div>
                        <div>
                           <div className="cb-section-title">Le tue Task</div>
                           <div className="cb-section-subtitle">{tasks.length} da completare</div>
                        </div>
                     </div>
                     <button className="cb-icon-btn" onClick={loadTasks} title="Aggiorna">
                        <i className={`ri-refresh-line${loadingTasks ? ' cb-spin' : ''}`}></i>
                     </button>
                  </div>

                  <div className="cb-scroll-body">
                     {loadingTasks && tasks.length === 0 ? (
                        <div className="cb-loading">
                           <div className="cb-spinner"></div>
                           <p>Caricamento task...</p>
                        </div>
                     ) : tasks.length === 0 ? (
                        <div className="cb-empty">
                           <div className="cb-empty-icon">
                              <i className="ri-checkbox-circle-line"></i>
                           </div>
                           <h6>Tutto fatto!</h6>
                           <p>Non hai attività in sospeso</p>
                           <Link to="/task" className="cb-task-link" style={{ maxWidth: '180px' }}>
                              <i className="ri-arrow-right-line"></i> Vedi archivio
                           </Link>
                        </div>
                     ) : (
                        <div className="cb-task-list">
                           {tasks.map((task) => {
                              const category = TASK_CATEGORIES[task.category] || { label: 'Generico', icon: 'ri-checkbox-blank-circle-line' };
                              const priority = TASK_PRIORITIES[task.priority] || { label: 'Bassa', color: '#6c757d' };
                              const badgeStyle = getCategoryBadgeStyle(task.category);

                              return (
                                 <div
                                    key={task.id}
                                    className="cb-task-card"
                                    onClick={(e) => { if (e.target.closest('.cb-task-check')) return; setSelectedTask(task); }}
                                 >
                                    <div className="cb-task-row">
                                       <div
                                          className="cb-task-check"
                                          onClick={() => toggleTaskCompletion(task.id, task.completed)}
                                          role="checkbox"
                                          aria-checked={false}
                                       />
                                       <div className="cb-task-body">
                                          <div className="cb-task-title">{task.title}</div>
                                          <div className="cb-task-badges">
                                             <span
                                                className="cb-task-badge"
                                                style={{ background: badgeStyle.bg, color: badgeStyle.color, borderColor: badgeStyle.border }}
                                             >
                                                <i className={category.icon}></i> {category.label}
                                             </span>
                                          </div>
                                       </div>
                                    </div>
                                 </div>
                              );
                           })}
                           <Link to="/task" className="cb-task-link">
                              <i className="ri-arrow-right-line"></i> Gestisci tutte le attività
                           </Link>
                        </div>
                     )}
                  </div>
               </div>
            </div>
         </div>

         {/* Task Detail Modal */}
         {selectedTask && (
            <div className="cb-modal-overlay" onClick={() => setSelectedTask(null)}>
               <div className="cb-modal" onClick={(e) => e.stopPropagation()}>
                  <div className="cb-modal-header">
                     <h5 className="cb-modal-title">{selectedTask.title}</h5>
                     <button className="cb-modal-close" onClick={() => setSelectedTask(null)}>
                        <i className="ri-close-line"></i>
                     </button>
                  </div>
                  <div className="cb-modal-body">
                     <span className="cb-modal-label">Descrizione</span>
                     <p className="cb-modal-text">
                        {selectedTask.description || "Nessuna descrizione."}
                     </p>
                     <div className="cb-modal-meta">
                        <span
                           className="cb-task-badge"
                           style={{
                              ...(() => { const s = getCategoryBadgeStyle(selectedTask.category); return { background: s.bg, color: s.color, borderColor: s.border }; })()
                           }}
                        >
                           <i className={(TASK_CATEGORIES[selectedTask.category] || {}).icon}></i>
                           {(TASK_CATEGORIES[selectedTask.category] || { label: selectedTask.category }).label}
                        </span>
                        <span className="cb-task-badge" style={{ background: '#f5f5f5', color: '#616161', borderColor: '#e0e0e0' }}>
                           {(TASK_PRIORITIES[selectedTask.priority] || { label: 'Bassa' }).label}
                        </span>
                     </div>
                     {selectedTask.client_name && (
                        <div style={{ fontSize: '13px', color: '#334155', marginBottom: '8px' }}>
                           <strong>Cliente:</strong> {selectedTask.client_name}
                        </div>
                     )}
                     <div style={{ fontSize: '12px', color: '#94a3b8' }}>
                        Scadenza: {selectedTask.due_date ? new Date(selectedTask.due_date).toLocaleDateString('it-IT') : 'Nessuna'}
                     </div>
                  </div>
                  <div className="cb-modal-footer">
                     <button className="cb-modal-btn-close" onClick={() => setSelectedTask(null)}>Chiudi</button>
                     <button className="cb-modal-btn-action" onClick={handleModalToggle}>
                        {selectedTask.completed ? 'Segna Da Fare' : 'Completa'}
                     </button>
                  </div>
               </div>
            </div>
         )}
      </div>
   );
};

export default ChatBox;

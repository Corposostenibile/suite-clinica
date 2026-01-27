import React, { useState, useEffect, useCallback, useRef } from "react";
import { Link } from "react-router-dom";
import { Modal, Button, Badge } from "react-bootstrap";
import postitService, { POSTIT_COLORS } from "../../services/postitService";
import taskService, { TASK_PRIORITIES, TASK_CATEGORIES } from "../../services/taskService";

const ChatBox = ({ onClick, toggle }) => {
   const [toggleTab, settoggleTab] = useState("chat");

   // Post-it state
   const [postits, setPostits] = useState([]);
   const [loading, setLoading] = useState(false);
   const [showCreateForm, setShowCreateForm] = useState(false);
   const [editingPostit, setEditingPostit] = useState(null);
   const [formData, setFormData] = useState({ content: '', color: 'yellow' });
   const [actionLoading, setActionLoading] = useState(false);

   // Task Modal state
   const [selectedTask, setSelectedTask] = useState(null);
   const [showTaskModal, setShowTaskModal] = useState(false);

   const dataToggle = [
      { href: "#chat", name: "Chat", key: "chat" },
      { href: "#postit", name: "Post-it", key: "postit" },
      { href: "#alerts", name: "Task", key: "task" },
   ];

   const headerStyle = {
      background: 'linear-gradient(180deg, #1B5E20 0%, #0D3B12 100%)',
      padding: '16px',
      margin: 0,
   };

   const tabStyle = (isActive) => ({
      color: isActive ? '#fff' : 'rgba(255, 255, 255, 0.7)',
      fontWeight: isActive ? 600 : 400,
      background: 'transparent',
      border: 'none',
      borderBottom: isActive ? '2px solid #4CAF50' : '2px solid transparent',
      padding: '8px 16px',
      transition: 'all 0.2s ease',
   });

   const loadingTasksRef = useRef(false);
   const loadingPostitsRef = useRef(false);

   // Load post-its when tab is activated
   const loadPostits = useCallback(async () => {
      if (loadingPostitsRef.current) return;
      loadingPostitsRef.current = true;
      setLoading(true);
      try {
         const res = await postitService.getAll();
         setPostits(res.postits || []);
      } catch (err) {
         console.error('Errore caricamento post-it:', err);
      } finally {
         setLoading(false);
         loadingPostitsRef.current = false;
      }
   }, []);

   useEffect(() => {
      if (toggleTab === 'postit' && toggle === 'chatbox') {
         loadPostits();
      }
   }, [toggleTab, toggle, loadPostits]);

   // Create post-it
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
         }
      } catch (err) {
         console.error('Errore creazione post-it:', err);
         alert('Errore nella creazione del post-it');
      } finally {
         setActionLoading(false);
      }
   };

   // Update post-it
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
      } finally {
         setActionLoading(false);
      }
   };

   // Delete post-it
   const handleDelete = async (id) => {
      if (actionLoading) return;
      if (!window.confirm('Eliminare questo post-it?')) return;

      setActionLoading(true);
      try {
         const res = await postitService.delete(id);
         if (res.success) {
            setPostits(prev => prev.filter(p => p.id !== id));
         }
      } catch (err) {
         console.error('Errore eliminazione post-it:', err);
         alert('Errore nell\'eliminazione del post-it');
      } finally {
         setActionLoading(false);
      }
   };

   // Start editing
   const startEdit = (postit) => {
      setEditingPostit(postit);
      setFormData({ content: postit.content, color: postit.color });
      setShowCreateForm(false);
   };

   // Cancel edit/create
   const cancelForm = () => {
      setEditingPostit(null);
      setShowCreateForm(false);
      setFormData({ content: '', color: 'yellow' });
   };

   // Task state
   const [tasks, setTasks] = useState([]);
   const [loadingTasks, setLoadingTasks] = useState(false);

   // Load tasks
   const loadTasks = useCallback(async () => {
      if (loadingTasksRef.current) return;
      
      loadingTasksRef.current = true;
      setLoadingTasks(true);
      try {
         // Get top 20 incomplete tasks
         const res = await taskService.getAll({ completed: 'false', per_page: 20 });
         setTasks(res || []);
      } catch (err) {
         console.error('Errore caricamento tasks:', err);
      } finally {
         setLoadingTasks(false);
         loadingTasksRef.current = false;
      }
   }, []);

   useEffect(() => {
      if (toggleTab === 'task' && toggle === 'chatbox') {
         loadTasks();
      }
   }, [toggleTab, toggle, loadTasks]);

   const toggleTaskCompletion = async (taskId, currentStatus) => {
      // Optimistic update
      setTasks(prev => prev.filter(t => t.id !== taskId)); // Remove from list instantly
      
      try {
         await taskService.toggleComplete(taskId, !currentStatus);
         // No need to reload, optimistic update is enough for sidebar
      } catch (err) {
         console.error("Error updating task:", err);
         if (err.response) {
            console.error("Response data:", err.response.data);
         }
         loadTasks(); // Revert on error
      }
   };

   const formatDate = (dateStr) => {
      if (!dateStr) return '';
      const date = new Date(dateStr);
      const today = new Date();
      const yesterday = new Date(today);
      yesterday.setDate(yesterday.getDate() - 1);

      if (date.toDateString() === today.toDateString()) {
         return 'Oggi';
      } else if (date.toDateString() === yesterday.toDateString()) {
         return 'Ieri';
      } else {
         return date.toLocaleDateString('it-IT', { day: 'numeric', month: 'short' });
      }
   };

   const openTaskModal = (task) => {
      setSelectedTask(task);
      setShowTaskModal(true);
   };

   const closeTaskModal = () => {
      setShowTaskModal(false);
      setSelectedTask(null);
   };

   return (
      <div className={`chatbox ${toggle === "chatbox" ? "active" : ""}`}>
         <div className="chatbox-close" onClick={() => onClick()}></div>
         <div className="custom-tab-1">
            <ul className="nav nav-tabs" style={headerStyle}>
               {dataToggle.map((data, i) => (
                  <li className="nav-item" key={i}>
                     <Link
                        className="nav-link"
                        style={tabStyle(toggleTab === data.key)}
                        to="#"
                        data-toggle="tab"
                        href={data.href}
                        onClick={() => settoggleTab(data.key)}
                     >
                        {data.name}
                     </Link>
                  </li>
               ))}
            </ul>
            <div className="tab-content">
               {/* Post-it Tab */}
               <div
                  className={`tab-pane fade ${toggleTab === "postit" ? "active show" : ""}`}
                  id="postit"
                  role="tabpanel"
               >
                  <div className="card mb-sm-3 mb-md-0 note_card">
                     <div className="card-header chat-list-header text-center">
                        <Link
                           to="#"
                           onClick={(e) => {
                              e.preventDefault();
                              setShowCreateForm(true);
                              setEditingPostit(null);
                              setFormData({ content: '', color: 'yellow' });
                           }}
                           style={{ color: showCreateForm ? '#4CAF50' : undefined }}
                        >
                           <i className="ri-add-line" style={{ fontSize: '18px' }}></i>
                        </Link>
                        <div>
                           <h6 className="mb-1">Post-it</h6>
                           <p className="mb-0">{postits.length} promemoria</p>
                        </div>
                        <Link to="#" onClick={loadPostits} style={{ opacity: loading ? 0.5 : 1 }}>
                           <i className={`ri-refresh-line ${loading ? 'spin' : ''}`} style={{ fontSize: '18px' }}></i>
                        </Link>
                     </div>

                     <div className="card-body contacts_body p-0 dz-scroll" id="DZ_W_Contacts_Body1" style={{ maxHeight: '450px' }}>
                        {/* Create/Edit Form */}
                        {(showCreateForm || editingPostit) && (
                           <div style={{ padding: '12px', borderBottom: '1px solid #e9ecef', background: '#f8f9fa' }}>
                              <form onSubmit={editingPostit ? handleUpdate : handleCreate}>
                                 <textarea
                                    value={formData.content}
                                    onChange={(e) => setFormData({ ...formData, content: e.target.value })}
                                    placeholder="Scrivi il tuo promemoria..."
                                    rows={3}
                                    style={{
                                       width: '100%',
                                       border: '1px solid #ddd',
                                       borderRadius: '8px',
                                       padding: '10px',
                                       fontSize: '13px',
                                       resize: 'none',
                                       marginBottom: '8px',
                                       background: POSTIT_COLORS[formData.color]?.bg || '#fff9c4'
                                    }}
                                    autoFocus
                                 />
                                 {/* Color picker */}
                                 <div className="d-flex gap-1 mb-2">
                                    {Object.entries(POSTIT_COLORS).map(([key, val]) => (
                                       <button
                                          key={key}
                                          type="button"
                                          onClick={() => setFormData({ ...formData, color: key })}
                                          style={{
                                             width: '24px',
                                             height: '24px',
                                             borderRadius: '50%',
                                             background: val.bg,
                                             border: formData.color === key ? `2px solid ${val.border}` : '1px solid #ddd',
                                             cursor: 'pointer',
                                             transition: 'transform 0.1s',
                                             transform: formData.color === key ? 'scale(1.1)' : 'scale(1)'
                                          }}
                                          title={val.label}
                                       />
                                    ))}
                                 </div>
                                 <div className="d-flex gap-2">
                                    <button
                                       type="submit"
                                       className="btn btn-sm btn-success flex-grow-1"
                                       disabled={!formData.content.trim() || actionLoading}
                                    >
                                       {actionLoading ? (
                                          <i className="ri-loader-4-line spin"></i>
                                       ) : editingPostit ? (
                                          <>
                                             <i className="ri-check-line me-1"></i>Salva
                                          </>
                                       ) : (
                                          <>
                                             <i className="ri-add-line me-1"></i>Crea
                                          </>
                                       )}
                                    </button>
                                    <button
                                       type="button"
                                       className="btn btn-sm btn-outline-secondary"
                                       onClick={cancelForm}
                                    >
                                       <i className="ri-close-line"></i>
                                    </button>
                                 </div>
                              </form>
                           </div>
                        )}

                        {/* Post-it List */}
                        {loading && postits.length === 0 ? (
                           <div className="text-center py-4">
                              <i className="ri-loader-4-line spin" style={{ fontSize: '24px', color: '#6c757d' }}></i>
                              <p className="text-muted mt-2 mb-0">Caricamento...</p>
                           </div>
                        ) : postits.length === 0 ? (
                           <div className="text-center py-4">
                              <i className="ri-sticky-note-line" style={{ fontSize: '48px', color: '#e9ecef' }}></i>
                              <p className="text-muted mt-2 mb-0">Nessun post-it</p>
                              <button
                                 className="btn btn-sm btn-success mt-2"
                                 onClick={() => setShowCreateForm(true)}
                              >
                                 <i className="ri-add-line me-1"></i>Crea il primo
                              </button>
                           </div>
                        ) : (
                           <ul className="contacts" style={{ listStyle: 'none', padding: 0, margin: 0 }}>
                              {postits.map((postit) => (
                                 <li
                                    key={postit.id}
                                    style={{
                                       padding: '12px 16px',
                                       borderBottom: '1px solid #f1f5f9',
                                       background: POSTIT_COLORS[postit.color]?.bg || '#fff9c4',
                                       borderLeft: `4px solid ${POSTIT_COLORS[postit.color]?.border || '#fdd835'}`
                                    }}
                                 >
                                    <div className="d-flex bd-highlight">
                                       <div className="user_info" style={{ flex: 1, minWidth: 0 }}>
                                          <span style={{
                                             display: 'block',
                                             fontSize: '13px',
                                             color: '#333',
                                             whiteSpace: 'pre-wrap',
                                             wordBreak: 'break-word'
                                          }}>
                                             {postit.content}
                                          </span>
                                          <p style={{
                                             margin: '4px 0 0',
                                             fontSize: '11px',
                                             color: '#888'
                                          }}>
                                             {formatDate(postit.createdAt)}
                                          </p>
                                       </div>
                                       <div className="ms-auto d-flex gap-1" style={{ marginLeft: '8px' }}>
                                          <button
                                             className="btn btn-primary btn-xs sharp"
                                             onClick={() => startEdit(postit)}
                                             title="Modifica"
                                             style={{ width: '28px', height: '28px' }}
                                          >
                                             <i className="ri-edit-line"></i>
                                          </button>
                                          <button
                                             className="btn btn-danger btn-xs sharp"
                                             onClick={() => handleDelete(postit.id)}
                                             title="Elimina"
                                             style={{ width: '28px', height: '28px' }}
                                          >
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
               </div>

               {/* Task Tab */}
               <div
                  className={`tab-pane fade ${toggleTab === "task" ? "active show" : ""}`}
                  id="alerts"
                  role="tabpanel"
               >
                  <div className="card mb-sm-3 mb-md-0 contacts_card">
                     <div className="card-header chat-list-header text-center">
                        <Link to="/task"><i className="ri-external-link-line" style={{ fontSize: '18px' }}></i></Link>
                        <div>
                           <h6 className="mb-1">Le tue Task</h6>
                           <p className="mb-0">{tasks.length} da completare</p>
                        </div>
                        <Link to="#" onClick={loadTasks} style={{ opacity: loadingTasks ? 0.5 : 1 }}>
                           <i className={`ri-refresh-line ${loadingTasks ? 'spin' : ''}`} style={{ fontSize: '18px' }}></i>
                        </Link>
                     </div>
                     <div className="card-body contacts_body p-0 dz-scroll" id="DZ_W_Contacts_Body2" style={{ maxHeight: '450px', background: '#f8faf9' }}>
                        {loadingTasks && tasks.length === 0 ? (
                           <div className="text-center py-4">
                              <i className="ri-loader-4-line spin" style={{ fontSize: '24px', color: '#6c757d' }}></i>
                              <p className="text-muted mt-2 mb-0">Caricamento...</p>
                           </div>
                        ) : tasks.length === 0 ? (
                           <div className="text-center py-4">
                              <i className="ri-task-line" style={{ fontSize: '48px', color: '#e9ecef' }}></i>
                              <p className="text-muted mt-2 mb-0">Nessun task in sospeso</p>
                           </div>
                        ) : (
                           <ul className="contacts" style={{ listStyle: 'none', padding: 0, margin: 0 }}>
                              {tasks.map((task) => (
                                 <li key={task.id} style={{
                                    padding: '12px 16px',
                                    borderBottom: '1px solid #f1f5f9',
                                    background: '#fff',
                                    display: 'flex',
                                    alignItems: 'flex-start',
                                    gap: '10px',
                                    cursor: 'pointer',
                                    transition: 'background 0.2s'
                                 }}
                                 onClick={(e) => {
                                    // Prevent modal if clicking checkbox
                                    if(e.target.type !== 'checkbox') {
                                       openTaskModal(task);
                                    }
                                 }}
                                 className="task-item-hover"
                                 >
                                    <div className="form-check m-0 pt-1">
                                       <input
                                          className="form-check-input"
                                          type="checkbox"
                                          checked={task.completed}
                                          onChange={() => toggleTaskCompletion(task.id, task.completed)}
                                          style={{ cursor: 'pointer' }}
                                       />
                                    </div>
                                    <div style={{ flex: 1, minWidth: 0 }}>
                                       <div className="d-flex justify-content-between align-items-start mb-1">
                                          <span style={{
                                             fontSize: '13px',
                                             fontWeight: 600,
                                             color: '#333',
                                             lineHeight: 1.3
                                          }}>
                                             {task.title}
                                          </span>
                                       </div>
                                       
                                       {/* Description removed for cleaner look, available in modal */}
                                       
                                       <div className="d-flex align-items-center gap-2 mt-1">
                                          {/* Priority Dot */}
                                          <div className="d-flex align-items-center" title={`Priorità: ${task.priority}`}>
                                             <div style={{
                                                width: '6px',
                                                height: '6px',
                                                borderRadius: '50%',
                                                backgroundColor: TASK_PRIORITIES[task.priority]?.color || '#6c757d',
                                                marginRight: '4px'
                                             }}></div>
                                             <span style={{ fontSize: '10px', color: '#888' }}>
                                                {task.due_date ? formatDate(task.due_date) : 'No scadenza'}
                                             </span>
                                          </div>
                                          
                                          {/* Category Badge */}
                                          <span className="badge border" style={{ 
                                             fontSize: '9px', 
                                             padding: '2px 6px',
                                             color: '#6c757d',
                                             fontWeight: 400
                                          }}>
                                             {task.category}
                                          </span>
                                       </div>
                                    </div>
                                 </li>
                              ))}
                           </ul>
                        )}
                        <div className="text-center p-3">
                           <Link to="/task" className="btn btn-xs btn-outline-primary rounded-pill w-100">
                              Vedi Tutti
                           </Link>
                        </div>
                     </div>
                  </div>
               </div>

               {/* Chat Tab - Coming Soon */}
               <div
                  className={`tab-pane fade ${toggleTab === "chat" ? "active show" : ""}`}
                  id="chat"
                  role="tabpanel"
               >
                  <div className="card mb-sm-3 mb-md-0 contacts_card dz-chat-user-box">
                     <div className="card-header chat-list-header text-center">
                        <Link to="/chat"><i className="ri-external-link-line" style={{ fontSize: '18px' }}></i></Link>
                        <div>
                           <h6 className="mb-1">Chat Pazienti</h6>
                           <p className="mb-0">Messaggi</p>
                        </div>
                        <span style={{ width: '18px' }}></span>
                     </div>
                     <div className="card-body contacts_body p-0 dz-scroll d-flex flex-column align-items-center justify-content-center text-center"
                          id="DZ_W_Contacts_Body"
                          style={{
                             minHeight: '350px',
                             background: 'linear-gradient(180deg, #f8faf9 0%, #ffffff 100%)',
                             padding: '30px 20px'
                          }}
                     >
                        {/* Icon */}
                        <div
                           style={{
                              width: '80px',
                              height: '80px',
                              borderRadius: '50%',
                              background: 'linear-gradient(135deg, rgba(40, 199, 111, 0.15) 0%, rgba(40, 199, 111, 0.05) 100%)',
                              display: 'flex',
                              alignItems: 'center',
                              justifyContent: 'center',
                              marginBottom: '16px'
                           }}
                        >
                           <i className="ri-chat-3-line" style={{ fontSize: '36px', color: '#28c76f' }}></i>
                        </div>

                        {/* Title */}
                        <h6 style={{ fontWeight: 600, color: '#333', fontSize: '16px', marginBottom: '8px' }}>
                           Chat con i Pazienti
                        </h6>

                        {/* Description */}
                        <p style={{
                           color: '#6c757d',
                           fontSize: '13px',
                           lineHeight: 1.5,
                           marginBottom: '16px',
                           maxWidth: '220px'
                        }}>
                           Questa funzionalità sarà disponibile con l'uscita dell'app pazienti.
                        </p>

                        {/* Feature Pills */}
                        <div className="d-flex flex-wrap justify-content-center gap-1 mb-3">
                           <span className="badge" style={{ background: 'rgba(40, 199, 111, 0.1)', color: '#28c76f', padding: '5px 10px', borderRadius: '12px', fontSize: '11px' }}>
                              <i className="ri-message-3-line me-1"></i>Real-time
                           </span>
                           <span className="badge" style={{ background: 'rgba(23, 162, 184, 0.1)', color: '#17a2b8', padding: '5px 10px', borderRadius: '12px', fontSize: '11px' }}>
                              <i className="ri-notification-3-line me-1"></i>Push
                           </span>
                           <span className="badge" style={{ background: 'rgba(255, 159, 67, 0.1)', color: '#ff9f43', padding: '5px 10px', borderRadius: '12px', fontSize: '11px' }}>
                              <i className="ri-attachment-2 me-1"></i>File
                           </span>
                        </div>

                        {/* Coming Soon Badge */}
                        <div
                           style={{
                              background: 'linear-gradient(135deg, #28c76f 0%, #24b662 100%)',
                              color: '#fff',
                              padding: '8px 18px',
                              borderRadius: '20px',
                              fontWeight: 600,
                              fontSize: '12px',
                              boxShadow: '0 3px 10px rgba(40, 199, 111, 0.3)',
                              display: 'inline-flex',
                              alignItems: 'center'
                           }}
                        >
                           <i className="ri-time-line me-1" style={{ fontSize: '14px' }}></i>
                           Prossimamente
                        </div>
                     </div>
                  </div>
               </div>
            </div>
         </div>

         {/* Task Details Modal */}
         <Modal show={showTaskModal} onHide={closeTaskModal} centered>
            <Modal.Header closeButton>
               <Modal.Title>{selectedTask?.title}</Modal.Title>
            </Modal.Header>
            <Modal.Body>
               {selectedTask && (
                  <div>
                     <div className="d-flex justify-content-between mb-3">
                        <Badge bg={TASK_CATEGORIES[selectedTask.category]?.bg || 'secondary'}>
                           <i className={`${TASK_CATEGORIES[selectedTask.category]?.icon} me-1`}></i>
                           {selectedTask.category}
                        </Badge>
                        <Badge bg="light" text="dark" className="border">
                           Priorità: {TASK_PRIORITIES[selectedTask.priority]?.label}
                        </Badge>
                     </div>
                     
                     <h6 className="fw-bold">Descrizione</h6>
                     <p style={{ whiteSpace: 'pre-wrap', color: '#555' }}>
                        {selectedTask.description || "Nessuna descrizione."}
                     </p>

                     {selectedTask.client_name && (
                        <div className="mt-3">
                           <strong>Cliente:</strong> {selectedTask.client_name}
                        </div>
                     )}

                     <div className="mt-3 text-muted small">
                        Creato il: {new Date(selectedTask.created_at).toLocaleDateString()}<br/>
                        Scadenza: {selectedTask.due_date ? new Date(selectedTask.due_date).toLocaleDateString() : 'Nessuna'}
                     </div>
                  </div>
               )}
            </Modal.Body>
            <Modal.Footer>
               <Button variant="secondary" onClick={closeTaskModal}>
                  Chiudi
               </Button>
               <Button 
                  variant="success" 
                  onClick={() => {
                     toggleTaskCompletion(selectedTask.id, selectedTask.completed);
                     closeTaskModal();
                  }}
               >
                  {selectedTask?.completed ? 'Segna come Da Fare' : 'Segna come Completato'}
               </Button>
            </Modal.Footer>
         </Modal>
      </div>
   );
};

export default ChatBox;

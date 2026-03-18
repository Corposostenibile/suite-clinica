import React, { useState, useEffect, useCallback, useRef } from "react";
import { Link } from "react-router-dom";
import { Modal, Button, Badge } from "react-bootstrap";
import taskService, { TASK_PRIORITIES, TASK_CATEGORIES } from "../../services/taskService";

const TaskSidebar = ({ isActive, toggle, openTaskModal }) => {
   const [tasks, setTasks] = useState([]);
   const [loadingTasks, setLoadingTasks] = useState(false);
   const loadingTasksRef = useRef(false);

   // Load tasks
   const loadTasks = useCallback(async () => {
      if (loadingTasksRef.current) return;
      
      loadingTasksRef.current = true;
      setLoadingTasks(true);
      try {
         // Get top 20 incomplete tasks
         const res = await taskService.getAll({
            completed: 'false',
            mine: 'true',
            paginate: 'true',
            page: 1,
            per_page: 20
         });
         setTasks(Array.isArray(res) ? (res || []) : (res?.items || []));
      } catch (err) {
         console.error('Errore caricamento tasks:', err);
      } finally {
         setLoadingTasks(false);
         loadingTasksRef.current = false;
      }
   }, []);

   useEffect(() => {
      if (isActive && toggle === 'chatbox') {
         loadTasks();
      }
   }, [isActive, toggle, loadTasks]);

   const toggleTaskCompletion = async (taskId, currentStatus) => {
      // Optimistic update
      setTasks(prev => prev.filter(t => t.id !== taskId)); 
      
      try {
         await taskService.toggleComplete(taskId, !currentStatus);
      } catch (err) {
         console.error("Error updating task:", err);
         loadTasks(); // Revert on error
      }
   };

   // Skeleton Loader Component
   const SkeletonLoader = () => (
      <div className="p-3">
         {[1, 2, 3].map(i => (
            <div key={i} className="mb-3 p-3 bg-white rounded shadow-sm border border-light">
               <div className="d-flex align-items-center mb-2">
                  <div className="bg-light rounded-circle me-2" style={{width: '18px', height: '18px'}}></div>
                  <div className="bg-light rounded" style={{height: '14px', width: '70%'}}></div>
               </div>
               <div className="bg-light rounded mt-2" style={{height: '10px', width: '40%'}}></div>
            </div>
         ))}
      </div>
   );

   return (
      <div className="card mb-sm-3 mb-md-0 contacts_card border-0 h-100 bg-light">
         {/* Header */}
         <div className="card-header bg-white border-bottom py-3 px-4 d-flex align-items-center justify-content-between shadow-sm sticky-top" style={{zIndex: 2}}>
             <div className="d-flex align-items-center gap-3">
                <div className="bg-primary bg-opacity-10 p-2 rounded-circle text-primary">
                    <i className="ri-task-line fs-5"></i>
                </div>
                <div>
                    <h6 className="mb-0 fw-bold text-dark">Le tue Task</h6>
                    <small className="text-muted fw-medium">{tasks.length} da completare</small>
                </div>
             </div>
            <Link 
                to="#" 
                onClick={loadTasks} 
                className={`btn btn-icon btn-ghost-secondary btn-sm rounded-circle ${loadingTasks ? 'spin' : ''}`}
                title="Aggiorna"
            >
               <i className="ri-refresh-line fs-5"></i>
            </Link>
         </div>

         {/* Body */}
         <div className="card-body p-0 dz-scroll bg-light" id="DZ_W_Contacts_Body2" style={{ maxHeight: 'calc(100vh - 160px)', overflowY: 'auto' }}>
            {loadingTasks && tasks.length === 0 ? (
               <SkeletonLoader />
            ) : tasks.length === 0 ? (
               <div className="d-flex flex-column align-items-center justify-content-center h-100 py-5 text-center px-4">
                  <div className="mb-3 bg-success bg-opacity-10 p-4 rounded-circle">
                      <i className="ri-checkbox-circle-line text-success" style={{ fontSize: '48px' }}></i>
                  </div>
                  <h6 className="fw-bold text-dark mb-1">Tutto fatto!</h6>
                  <p className="text-muted small mb-3">Non hai attività in sospeso per oggi.<br/>Ottimo lavoro!</p>
                  <Link to="/task" className="btn btn-sm btn-outline-primary px-4 rounded-pill">
                      Vedi archiviati
                  </Link>
               </div>
            ) : (
               <div className="p-3 d-flex flex-column gap-3">
                  {tasks.map((task) => {
                      const category = TASK_CATEGORIES[task.category] || { label: 'Generico', color: '#6c757d', bg: 'secondary', icon: 'ri-checkbox-blank-circle-line' };
                      const priority = TASK_PRIORITIES[task.priority] || { label: 'Bassa', color: '#6c757d' };
                      
                      return (
                         <div 
                            key={task.id} 
                            className="task-card bg-white rounded-3 p-3 shadow-sm border border-light position-relative overflow-hidden transition-all"
                            style={{ cursor: 'pointer', transition: 'all 0.2s ease', borderLeft: `4px solid ${priority.color}` }}
                            onClick={(e) => {
                               if(e.target.type !== 'checkbox') openTaskModal(task);
                            }}
                         >
                            <div className="d-flex align-items-start gap-3">
                               <div className="form-check m-0 pt-1">
                                  <input
                                     className="form-check-input shadow-none"
                                     type="checkbox"
                                     checked={task.completed}
                                     onChange={() => toggleTaskCompletion(task.id, task.completed)}
                                     style={{ cursor: 'pointer', width: '20px', height: '20px', borderRadius: '6px' }}
                                  />
                               </div>
                               <div className="flex-grow-1">
                                  <div className="d-flex justify-content-between align-items-start mb-1">
                                     <h6 className="mb-0 fw-semibold text-dark leading-tight" style={{fontSize: '14px', lineHeight: '1.4'}}>
                                         {task.title}
                                     </h6>
                                  </div>
                                  
                                  <div className="d-flex align-items-center flex-wrap gap-2 mt-2">
                                     <span className={`badge bg-${category.bg} bg-opacity-10 text-${category.bg} border border-${category.bg} border-opacity-25 px-2 py-1 rounded-pill d-flex align-items-center gap-1`} style={{fontSize: '10px', height: '20px'}}>
                                        <i className={category.icon}></i> {category.label}
                                     </span>
                                     
                                     {task.due_date && (
                                         <span className={`badge bg-light text-muted border px-2 py-1 rounded-pill d-flex align-items-center gap-1 ${new Date(task.due_date) < new Date() ? 'text-danger border-danger border-opacity-25 bg-danger bg-opacity-10' : ''}`} style={{fontSize: '10px', height: '20px'}}>
                                            <i className="ri-calendar-line"></i>
                                            {new Date(task.due_date).toLocaleDateString('it-IT', {day: 'numeric', month: 'short'})}
                                         </span>
                                     )}

                                     <span className="ms-auto badge bg-white border text-muted px-2 py-1 rounded-pill" style={{fontSize: '10px', height: '20px', color: priority.color}}>
                                         {priority.label}
                                     </span>
                                  </div>
                               </div>
                            </div>
                         </div>
                      );
                  })}
                  
                  <Link to="/task" className="btn btn-outline-primary btn-sm rounded-pill w-100 mt-2 py-2 fw-medium">
                      <i className="ri-arrow-right-line me-1"></i> Gestisci tutte le attività
                  </Link>
               </div>
            )}
         </div>
      </div>
   );
};

export default TaskSidebar;

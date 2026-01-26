import React, { useState } from "react";
import { Link } from "react-router-dom";

// Avatar images
import avatar1 from "../../images/avatar/1.png";
import avatar2 from "../../images/avatar/2.png";
import avatar3 from "../../images/avatar/3.png";
import avatar4 from "../../images/avatar/4.png";
import avatar5 from "../../images/avatar/5.png";
import avatar6 from "../../images/profile/2.jpg";
import avatar7 from "../../images/profile/3.jpg";
import avatar8 from "../../images/profile/4.jpg";

// Mock chat data
const chatData = [
   { id: 1, name: 'Marco Rossi', avatar: avatar1, lastMessage: 'Grazie mille, a domani!', unread: 3 },
   { id: 2, name: 'Laura Bianchi', avatar: avatar2, lastMessage: 'Ho completato il check settimanale', unread: 1 },
   { id: 3, name: 'Giuseppe Verdi', avatar: avatar3, lastMessage: 'Perfetto, grazie per le indicazioni', unread: 0 },
   { id: 4, name: 'Anna Ferrari', avatar: avatar4, lastMessage: 'Possiamo spostare l\'appuntamento?', unread: 2 },
   { id: 5, name: 'Paolo Esposito', avatar: avatar5, lastMessage: 'Ok, confermo la dieta', unread: 0 },
   { id: 6, name: 'Francesca Romano', avatar: avatar6, lastMessage: 'Buongiorno, ho una domanda...', unread: 0 },
   { id: 7, name: 'Luigi Conte', avatar: avatar7, lastMessage: 'Ricevuto, grazie!', unread: 0 },
   { id: 8, name: 'Maria Greco', avatar: avatar8, lastMessage: 'Come procedo con gli esercizi?', unread: 5 },
];

const ChatBox = ({ onClick, toggle }) => {
   const [toggleTab, settoggleTab] = useState("chat");

   const dataToggle = [
      { href: "#chat", name: "Chat", key: "chat" },
      { href: "#notes", name: "Note", key: "note" },
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
               {/* Notes Tab */}
               <div
                  className={`tab-pane fade ${toggleTab === "note" ? "active show" : ""}`}
                  id="notes"
                  role="tabpanel"
               >
                  <div className="card mb-sm-3 mb-md-0 note_card">
                     <div className="card-header chat-list-header text-center">
                        <Link to="#"><i className="ri-add-line" style={{ fontSize: '18px' }}></i></Link>
                        <div>
                           <h6 className="mb-1">Note Personali</h6>
                           <p className="mb-0">I tuoi promemoria</p>
                        </div>
                        <Link to="#"><i className="ri-search-line" style={{ fontSize: '18px' }}></i></Link>
                     </div>
                     <div className="card-body contacts_body p-0 dz-scroll" id="DZ_W_Contacts_Body1">
                        <ul className="contacts">
                           <li className="active">
                              <div className="d-flex bd-highlight">
                                 <div className="user_info">
                                    <span>Chiamare Marco Rossi</span>
                                    <p>Oggi, 10:30</p>
                                 </div>
                                 <div className="ms-auto">
                                    <Link to="#" className="btn btn-primary btn-xs sharp me-1"><i className="ri-edit-line"></i></Link>
                                    <Link to="#" className="btn btn-danger btn-xs sharp"><i className="ri-delete-bin-line"></i></Link>
                                 </div>
                              </div>
                           </li>
                           <li>
                              <div className="d-flex bd-highlight">
                                 <div className="user_info">
                                    <span>Preparare piano alimentare</span>
                                    <p>Domani, 09:00</p>
                                 </div>
                                 <div className="ms-auto">
                                    <Link to="#" className="btn btn-primary btn-xs sharp me-1"><i className="ri-edit-line"></i></Link>
                                    <Link to="#" className="btn btn-danger btn-xs sharp"><i className="ri-delete-bin-line"></i></Link>
                                 </div>
                              </div>
                           </li>
                           <li>
                              <div className="d-flex bd-highlight">
                                 <div className="user_info">
                                    <span>Riunione team nutrizione</span>
                                    <p>Lunedì, 14:00</p>
                                 </div>
                                 <div className="ms-auto">
                                    <Link to="#" className="btn btn-primary btn-xs sharp me-1"><i className="ri-edit-line"></i></Link>
                                    <Link to="#" className="btn btn-danger btn-xs sharp"><i className="ri-delete-bin-line"></i></Link>
                                 </div>
                              </div>
                           </li>
                        </ul>
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
                           <p className="mb-0">Da completare</p>
                        </div>
                        <Link to="#"><i className="ri-check-double-line" style={{ fontSize: '18px' }}></i></Link>
                     </div>
                     <div className="card-body contacts_body p-0 dz-scroll" id="DZ_W_Contacts_Body2">
                        <ul className="contacts">
                           <li className="name-first-letter">ONBOARDING</li>
                           <li className="active">
                              <div className="d-flex bd-highlight">
                                 <div className="img_cont primary"><i className="ri-user-add-line"></i></div>
                                 <div className="user_info">
                                    <span>Messaggio di benvenuto</span>
                                    <p>Marco Rossi</p>
                                 </div>
                              </div>
                           </li>
                           <li className="name-first-letter">CHECK</li>
                           <li>
                              <div className="d-flex bd-highlight">
                                 <div className="img_cont success"><i className="ri-file-list-3-line"></i></div>
                                 <div className="user_info">
                                    <span>Nuovo check da leggere</span>
                                    <p>Laura Bianchi</p>
                                 </div>
                              </div>
                           </li>
                           <li>
                              <div className="d-flex bd-highlight">
                                 <div className="img_cont success"><i className="ri-file-list-3-line"></i></div>
                                 <div className="user_info">
                                    <span>Nuovo check da leggere</span>
                                    <p>Giuseppe Verdi</p>
                                 </div>
                              </div>
                           </li>
                           <li className="name-first-letter">REMINDER</li>
                           <li>
                              <div className="d-flex bd-highlight">
                                 <div className="img_cont warning"><i className="ri-alarm-warning-line"></i></div>
                                 <div className="user_info">
                                    <span>Check mancante, sollecita!</span>
                                    <p>Anna Ferrari</p>
                                 </div>
                              </div>
                           </li>
                        </ul>
                     </div>
                  </div>
               </div>

               {/* Chat Tab */}
               <div
                  className={`tab-pane fade ${toggleTab === "chat" ? "active show" : ""}`}
                  id="chat"
                  role="tabpanel"
               >
                  <div className="card mb-sm-3 mb-md-0 contacts_card dz-chat-user-box">
                     <div className="card-header chat-list-header text-center">
                        <Link to="/chat"><i className="ri-external-link-line" style={{ fontSize: '18px' }}></i></Link>
                        <div>
                           <h6 className="mb-1">Conversazioni</h6>
                           <p className="mb-0">Clienti Attivi</p>
                        </div>
                        <Link to="#"><i className="ri-search-line" style={{ fontSize: '18px' }}></i></Link>
                     </div>
                     <div className="card-body contacts_body p-0 dz-scroll" id="DZ_W_Contacts_Body">
                        <ul className="contacts" style={{ listStyle: 'none', padding: 0, margin: 0 }}>
                           {chatData.map((chat) => (
                              <li
                                 key={chat.id}
                                 className="dz-chat-user"
                                 style={{
                                    padding: '12px 16px',
                                    borderBottom: '1px solid #f1f5f9',
                                    cursor: 'pointer',
                                    transition: 'background 0.2s'
                                 }}
                              >
                                 <div className="d-flex align-items-center">
                                    <div style={{ position: 'relative', marginRight: '12px' }}>
                                       <img
                                          src={chat.avatar}
                                          alt={chat.name}
                                          style={{
                                             width: '45px',
                                             height: '45px',
                                             borderRadius: '50%',
                                             objectFit: 'cover'
                                          }}
                                       />
                                       {chat.unread > 0 && (
                                          <span
                                             style={{
                                                position: 'absolute',
                                                top: '-4px',
                                                right: '-4px',
                                                background: '#4CAF50',
                                                color: '#fff',
                                                fontSize: '10px',
                                                fontWeight: 700,
                                                width: '18px',
                                                height: '18px',
                                                borderRadius: '50%',
                                                display: 'flex',
                                                alignItems: 'center',
                                                justifyContent: 'center',
                                             }}
                                          >
                                             {chat.unread}
                                          </span>
                                       )}
                                    </div>
                                    <div style={{ flex: 1, minWidth: 0 }}>
                                       <h6 style={{
                                          margin: 0,
                                          fontSize: '14px',
                                          fontWeight: chat.unread > 0 ? 600 : 500,
                                          color: '#1e293b'
                                       }}>
                                          {chat.name}
                                       </h6>
                                       <p style={{
                                          margin: 0,
                                          fontSize: '12px',
                                          color: chat.unread > 0 ? '#475569' : '#94a3b8',
                                          fontWeight: chat.unread > 0 ? 500 : 400,
                                          whiteSpace: 'nowrap',
                                          overflow: 'hidden',
                                          textOverflow: 'ellipsis'
                                       }}>
                                          {chat.lastMessage}
                                       </p>
                                    </div>
                                 </div>
                              </li>
                           ))}
                        </ul>
                     </div>
                  </div>
               </div>
            </div>
         </div>
      </div>
   );
};

export default ChatBox;

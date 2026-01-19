import React,{useReducer} from 'react';
import {Link} from 'react-router-dom';
import { Modal } from 'react-bootstrap';


import { ICONS } from '../../../constant/theme';

const svgBlogData = [
    {Iconname : 'Active-Call.svg', svgtype : ICONS.ActiveCall},
    {Iconname : 'Add-User.svg', svgtype : ICONS.AddUser},
    {Iconname : 'Address-Card.svg', svgtype : ICONS.AddressCard},
    {Iconname : 'AdressBook#1.svg', svgtype : ICONS.AdressBook_1},
    {Iconname : 'AdressBook#2.svg', svgtype : ICONS.AdressBook_2},
    {Iconname : 'Archive.svg', svgtype : ICONS.Archive},
    {Iconname : 'Call#1.svg', svgtype : ICONS.Call_1},
    {Iconname : 'Call.svg', svgtype : ICONS.Call},
    {Iconname : 'Chat#1.svg', svgtype : ICONS.Chat_1},
    {Iconname : 'Chat#2.svg', svgtype : ICONS.Chat_2},
    {Iconname : 'Chat#4.svg', svgtype : ICONS.Chat_4},
    {Iconname : 'Chat#5.svg', svgtype : ICONS.Chat_5},
    {Iconname : 'Chat#6.svg', svgtype : ICONS.Chat_6},
    {Iconname : 'Chat-Check.svg', svgtype : ICONS.ChatCheck},
    {Iconname : 'Chat-Error.svg', svgtype : ICONS.ChatError},
    {Iconname : 'Chat-Locked.svg', svgtype : ICONS.ChatLocked},
    {Iconname : 'Chat-Smile.svg', svgtype : ICONS.ChatSmile},
    {Iconname : 'Clipboard-Check.svg', svgtype : ICONS.ClipboardCheck},
    {Iconname : 'Clipboard-List.svg', svgtype : ICONS.ClipboardList},
    {Iconname : 'Contact#1.svg', svgtype : ICONS.Contact_1},
    {Iconname : 'Delete-User.svg', svgtype : ICONS.DeleteUser},
    {Iconname : 'Dial-Numbers.svg', svgtype : ICONS.DialNumbers},
    {Iconname : 'Flag.svg', svgtype : ICONS.Flag},
    {Iconname : 'Forward.svg', svgtype : ICONS.Forward},
    {Iconname : 'Group-Chat.svg', svgtype : ICONS.GroupChat},
    {Iconname : 'Group.svg', svgtype : ICONS.Group},
    {Iconname : 'Incoming-Box.svg', svgtype : ICONS.IncomingBox},
    {Iconname : 'Incoming-Call.svg', svgtype : ICONS.IncomingCall},
    {Iconname : 'Incoming-Mail.svg', svgtype : ICONS.IncomingMail},
    {Iconname : 'Mail@.svg', svgtype : ICONS.MailAt},
    {Iconname : 'Mail-Attachment.svg', svgtype : ICONS.MailAttachment},
    {Iconname : 'Mail-Box.svg', svgtype : ICONS.MailBox},
    {Iconname : 'Mail-Error.svg', svgtype : ICONS.MailError},
    {Iconname : 'Mail-Heart.svg', svgtype : ICONS.MailHeart},
    {Iconname : 'Mail-Locked.svg', svgtype : ICONS.MailLocked},
    {Iconname : 'Mail-Notification.svg', svgtype : ICONS.MailNotification},
    {Iconname : 'Mail-Opened.svg', svgtype : ICONS.MailOpened},
    {Iconname : 'Mail-Unocked.svg', svgtype : ICONS.MailUnocked},
    {Iconname : 'Mail.svg', svgtype : ICONS.Mail},
    {Iconname : 'Missed-Call.svg', svgtype : ICONS.MissedCall},
    {Iconname : 'Outgoing-Box.svg', svgtype : ICONS.OutgoingBox},
    {Iconname : 'Outgoing-Call.svg', svgtype : ICONS.OutgoingCall},
    {Iconname : 'Outgoing-Mail.svg', svgtype : ICONS.OutgoingMail},
    {Iconname : 'Readed-Mail.svg', svgtype : ICONS.ReadedMail},
    {Iconname : 'Reply-All.svg', svgtype : ICONS.ReplyAll},
    {Iconname : 'Reply.svg', svgtype : ICONS.Reply},
    {Iconname : 'Right.svg', svgtype : ICONS.Right},
    {Iconname : 'RSS.svg', svgtype : ICONS.RSS},
    {Iconname : 'Safe-Chat.svg', svgtype : ICONS.SafeChat},
    {Iconname : 'Send.svg', svgtype : ICONS.Send},
    {Iconname : 'Sending-Mail.svg', svgtype : ICONS.SendingMail},
    {Iconname : 'Sending.svg', svgtype : ICONS.Sending},
    {Iconname : 'Share.svg', svgtype : ICONS.Share},
    {Iconname : 'Shield-Thunder.svg', svgtype : ICONS.ShieldThunder},
    {Iconname : 'Shield-User.svg', svgtype : ICONS.ShieldUser},
    {Iconname : 'Snoozed-Mail.svg', svgtype : ICONS.SnoozedMail},
    {Iconname : 'Spam.svg', svgtype : ICONS.Spam},
    {Iconname : 'Thumbtack.svg', svgtype : ICONS.Thumbtack},
    {Iconname : 'Urgent-Mail.svg', svgtype : ICONS.UrgentMail},
    {Iconname : 'Write.svg', svgtype : ICONS.Write},
     
];

const Communication = () => {
    const initialState = false;
    const reducer = (state, action) =>{   
        switch (action.type){
            case 'imageModal':
                return { ...state, imageModal: !state.imageModal, content : action.content}
            case 'svgModal':
                return { ...state, svgModal: !state.svgModal, content : action.content, title: action.title}			
            default:
                return state
        }	
    }
    const [state, dispatch] = useReducer(reducer, initialState);
    return (
        <>
            <div className="card-header">Communication</div>
            <div className="row">							
                {svgBlogData.map((item, ind)=>(
                    <div className="col-xl-2 col-lg-4 col-xxl-2 col-md-6 col-sm-6 col-12 m-b20" key={ind}>	
                        <div className="svg-icons-ov">
                            <div className="svg-icons-prev">
                                <div dangerouslySetInnerHTML={{ __html: item.svgtype }} />                                                    
                            </div>
                            <div className="svg-classname">{item.Iconname}</div>
                            <div className="svg-icon-popup">
                                <Link to={"#"}  onClick={() => dispatch({type:'imageModal', content: item.Iconname })} className="btn btn-sm btn-brand"><i className="fa-solid fa-image"></i></Link>
                                <Link to={"#"} onClick={() => dispatch({type:'svgModal', content: item.Iconname, title : item.svgtype })} className="btn btn-sm btn-brand"><i className="fa fa-code"></i></Link>
                            </div>
                            
                        </div>
                    </div>
                ))}
            </div>
                           
                <Modal className="modal fade" show={state.imageModal} onHide={()=>dispatch({type:'imageModal'})} centered>                                
                    <div className="modal-content">
                        <div className="modal-header">
                            <h5 className="modal-title" id="svg_img_label_Brassieresvg">{state.content}</h5>
                            <button type="button" className="btn-close" onClick={() => dispatch({type:'imageModal'})}></button>
                        </div>
                        <div className="modal-body">                               
                            <pre>                           
{`import MyImage from "../icons/svgicons/${state.content}";
export default function Imageblog() {   
return  
    <div>
    <img src={MyImage} alt="Example" />   
    </div>
}`}
;
                            </pre>
                        </div>
                        <div className="modal-footer">
                            <button type="button" className="btn btn-secondary" onClick={() => dispatch({type:'imageModal'})}>Close</button>
                        </div>
                    </div>
                
                </Modal>
                <Modal className="modal fade" show={state.svgModal} onHide={()=>dispatch({type:'svgModal'})} centered >                    
                    <div className="modal-content">
                        <div className="modal-header">
                            <h5 className="modal-title" id="svg_inline_label_Brassieresvg">{state.content}</h5>
                            <button type="button" className="btn-close"   onClick={() => dispatch({type:'svgModal'})}>
                            </button>
                        </div>
                        <div className="modal-body">
<pre>   
{state.title}    
</pre>
                        </div>
                        <div className="modal-footer">
                            <button type="button" className="btn btn-secondary" onClick={() => dispatch({type:'svgModal'})}>Close</button>
                        </div>
                    </div>
                    
                </Modal>  
        </>
    );
};

export default Communication;
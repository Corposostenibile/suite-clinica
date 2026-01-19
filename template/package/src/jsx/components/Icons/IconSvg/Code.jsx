import React,{useReducer} from 'react';
import {Link} from 'react-router-dom';
import { Modal } from 'react-bootstrap';


import { ICONS } from '../../../constant/theme';

const svgBlogData = [
    {Iconname : 'Backspace.svg', svgtype : ICONS.Backspace},
    {Iconname : 'CMD.svg', svgtype : ICONS.CMD},
    {Iconname : 'Code.svg', svgtype : ICONS.Code},
    {Iconname : 'Commit.svg', svgtype : ICONS.Commit},
    {Iconname : 'Compiling.svg', svgtype : ICONS.Compiling},
    {Iconname : 'Control.svg', svgtype : ICONS.Control},
    {Iconname : 'Done-Circle.svg', svgtype : ICONS.DoneCircle},
    {Iconname : 'Error-Circle.svg', svgtype : ICONS.ErrorCircle},
    {Iconname : 'Git#1.svg', svgtype : ICONS.Git_1},
    {Iconname : 'Git#2.svg', svgtype : ICONS.Git_2},
    {Iconname : 'Git#3.svg', svgtype : ICONS.Git_3},
    {Iconname : 'Git#4.svg', svgtype : ICONS.Git_4},
    {Iconname : 'Github.svg', svgtype : ICONS.Github},
    {Iconname : 'Info-Circle.svg', svgtype : ICONS.InfoCircle},
    {Iconname : 'Left-Circle.svg', svgtype : ICONS.LeftCircle},
    {Iconname : 'Loading.svg', svgtype : ICONS.Loading},
    {Iconname : 'Lock-Circle.svg', svgtype : ICONS.LockCircle},
    {Iconname : 'Lock-Overturning.svg', svgtype : ICONS.LockOverturning},
    {Iconname : 'Minus.svg', svgtype : ICONS.Minus},
    {Iconname : 'Option.svg', svgtype : ICONS.Option},
    {Iconname : 'Plus.svg', svgtype : ICONS.Plus},
    {Iconname : 'Puzzle.svg', svgtype : ICONS.Puzzle},
    {Iconname : 'Question-Circle.svg', svgtype : ICONS.QuestionCircle},
    {Iconname : 'Right-Circle.svg', svgtype : ICONS.RightCircle},
    {Iconname : 'Settings#4.svg', svgtype : ICONS.Settings_4},
    {Iconname : 'Shift.svg', svgtype : ICONS.Shift},
    {Iconname : 'Spy.svg', svgtype : ICONS.Spy},
    {Iconname : 'Stop.svg', svgtype : ICONS.Stop},
    {Iconname : 'Terminal.svg', svgtype : ICONS.Terminal},
    {Iconname : 'Thunder-Circle.svg', svgtype : ICONS.ThunderCircle},
    {Iconname : 'Time-Schedule.svg', svgtype : ICONS.TimeSchedule},
    {Iconname : 'Warning-Circle.svg', svgtype : ICONS.Warning1Circle},
    {Iconname : 'Warning-2.svg', svgtype : ICONS.Warning2},    
];

const Code = () => {
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
            <div className="card-header">Code</div>
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

export default Code;
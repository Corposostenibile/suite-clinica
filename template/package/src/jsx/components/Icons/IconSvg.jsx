import React,{useReducer} from 'react';
import {Link} from 'react-router-dom';
import { Modal } from 'react-bootstrap';

import PageTitle from '../../layouts/PageTitle';
import { ICONS } from '../../constant/theme';
import Code from './IconSvg/Code';
import Communication from './IconSvg/Communication';
import Cooking from './IconSvg/Cooking';
import Design from './IconSvg/Design';
import Device from './IconSvg/Device';
import Electric from './IconSvg/Electric';
import Files from './IconSvg/Files';
import Food from './IconSvg/Food';
import General from './IconSvg/General';



const svgBlogData = [
    {Iconname : 'Brassiere.svg', svgtype : ICONS.Brassiere},
    {Iconname : 'Briefcase.svg', svgtype : ICONS.Briefcase},
    {Iconname : 'Cap.svg', svgtype : ICONS.Cap},
    {Iconname : 'Crown.svg', svgtype : ICONS.Crown},
    {Iconname : 'Dress.svg', svgtype : ICONS.Dress},
    {Iconname : 'Hanger.svg', svgtype : ICONS.Hanger},
    {Iconname : 'Hat.svg', svgtype : ICONS.Hat},
    {Iconname : 'Panties.svg', svgtype : ICONS.Panties},
    {Iconname : 'Shirt.svg', svgtype : ICONS.Shirt},
    {Iconname : 'Shoes.svg', svgtype : ICONS.Shoes},
    {Iconname : 'Shorts.svg', svgtype : ICONS.Shorts},
    {Iconname : 'Sneakers.svg', svgtype : ICONS.Sneakers},
    {Iconname : 'Socks.svg', svgtype : ICONS.Socks},
    {Iconname : 'SunGlasses.svg', svgtype : ICONS.SunGlasses},
    {Iconname : 'TShirt.svg', svgtype : ICONS.TShirt},
    {Iconname : 'Tie.svg', svgtype : ICONS.Tie},
    
];

const SvgIcons  = () => {
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
            <PageTitle activeMenu={"Svg Icons"} motherMenu={"Icons"} />
            <div className="card"> 
                <div className="card-body svg-area">
					<div className="card-header">Clothes</div>
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
                    <div className="sef-line"></div>
                    <Code />
                    <div className="sef-line"></div>
                    <Communication />
                    <div className="sef-line"></div>
                    <Cooking />
                    <div className="sef-line"></div>
                    <Design />
                    <div className="sef-line"></div>
                    <Device />
                    <div className="sef-line"></div>
                    <Electric />
                    <div className="sef-line"></div>
                    <Files />
                    <div className="sef-line"></div>
                    <Food />
                    <div className="sef-line"></div>
                    <General />

                </div>
            </div>
        </>
    );
};

export default SvgIcons ;
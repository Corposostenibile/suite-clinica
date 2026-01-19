import React,{useReducer} from 'react';
import {Link} from 'react-router-dom';
import { Modal } from 'react-bootstrap';

import { ICONS } from '../../../constant/theme';

const svgBlogData = [
    {Iconname : 'Adjust.svg', svgtype : ICONS.Adjust},
    {Iconname : 'Anchor-Center-Down.svg', svgtype : ICONS.AnchorCenterDown},
    {Iconname : 'Anchor-Center-Up.svg', svgtype : ICONS.AnchorCenterUp},
    {Iconname : 'Anchor-Center.svg', svgtype : ICONS.AnchorCenter},
    {Iconname : 'Anchor-Left-Down.svg', svgtype : ICONS.AnchorLeftDown},
    {Iconname : 'Anchor-Left-Up.svg', svgtype : ICONS.AnchorLeftUp},
    {Iconname : 'Anchor-Left.svg', svgtype : ICONS.AnchorLeft},
    {Iconname : 'Anchor-Right-Down.svg', svgtype : ICONS.AnchorRightDown},
    {Iconname : 'Anchor-Right-Up.svg', svgtype : ICONS.AnchorRightUp},
    {Iconname : 'Anchor-Right.svg', svgtype : ICONS.AnchorRight},
    {Iconname : 'Arrows.svg', svgtype : ICONS.Arrows},
    {Iconname : 'Bezier-Curve.svg', svgtype : ICONS.BezierCurve},
    {Iconname : 'Border.svg', svgtype : ICONS.Border},
    {Iconname : 'Brush.svg', svgtype : ICONS.Brush},
    {Iconname : 'Bucket.svg', svgtype : ICONS.Bucket},
    {Iconname : 'Cap-1.svg', svgtype : ICONS.Cap1},
    {Iconname : 'Cap-1.svg', svgtype : ICONS.Cap1},
    {Iconname : 'Cap-1.svg', svgtype : ICONS.Cap1},
    {Iconname : 'Circle.svg', svgtype : ICONS.Circle},
    {Iconname : 'Color-Profile.svg', svgtype : ICONS.ColorProfile},
    {Iconname : 'Color.svg', svgtype : ICONS.Color},
    {Iconname : 'Component.svg', svgtype : ICONS.Component},
    {Iconname : 'Crop.svg', svgtype : ICONS.Crop},
    {Iconname : 'Difference.svg', svgtype : ICONS.Difference},
    {Iconname : 'Edit.svg', svgtype : ICONS.Edit},
    {Iconname : 'Eraser.svg', svgtype : ICONS.Eraser},
    {Iconname : 'Flatten.svg', svgtype : ICONS.Flatten},
    {Iconname : 'Flip-Horizontal.svg', svgtype : ICONS.FlipHorizontal},
    {Iconname : 'Flip-Vertical.svg', svgtype : ICONS.FlipVertical},
    {Iconname : 'Horizontal.svg', svgtype : ICONS.Horizontal},
    {Iconname : 'Image.svg', svgtype : ICONS.Image},
    {Iconname : 'Interselect.svg', svgtype : ICONS.Interselect},
    {Iconname : 'Join-1.svg', svgtype : ICONS.Join1},
    {Iconname : 'Join-2.svg', svgtype : ICONS.Join2},
    {Iconname : 'Join-3.svg', svgtype : ICONS.Join3},
    {Iconname : 'Layers.svg', svgtype : ICONS.Layers},
    {Iconname : 'Line.svg', svgtype : ICONS.Line},
    {Iconname : 'Magic.svg', svgtype : ICONS.Magic},
    {Iconname : 'Mask.svg', svgtype : ICONS.Mask},
    {Iconname : 'Patch.svg', svgtype : ICONS.Patch},
    {Iconname : 'Pen_ruller.svg', svgtype : ICONS.Pen_ruller},
    {Iconname : 'Pen-Tool-Vector.svg', svgtype : ICONS.PenToolVector},
    {Iconname : 'Pencil.svg', svgtype : ICONS.Pencil},
    {Iconname : 'Picker.svg', svgtype : ICONS.Picker},
    {Iconname : 'Pixels.svg', svgtype : ICONS.Pixels},
    {Iconname : 'Polygon.svg', svgtype : ICONS.Polygon},
    {Iconname : 'Position.svg', svgtype : ICONS.Position},
    {Iconname : 'Rectangle.svg', svgtype : ICONS.Rectangle},
    {Iconname : 'Saturation.svg', svgtype : ICONS.Saturation},
    {Iconname : 'Select.svg', svgtype : ICONS.Select},
    {Iconname : 'Sketch.svg', svgtype : ICONS.Sketch},
    {Iconname : 'Stamp.svg', svgtype : ICONS.Stamp},
    {Iconname : 'Substract.svg', svgtype : ICONS.Substract},
    {Iconname : 'Target.svg', svgtype : ICONS.Target},
    {Iconname : 'Triangle.svg', svgtype : ICONS.Triangle},
    {Iconname : 'Union.svg', svgtype : ICONS.Union},
    {Iconname : 'Vertical.svg', svgtype : ICONS.Vertical},
    {Iconname : 'Zoom-Minus.svg', svgtype : ICONS.ZoomMinus},
    {Iconname : 'Zoom-Plus.svg', svgtype : ICONS.ZoomPlus},
    
    
];

const Design = () => {
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
            <div className="card-header">Design</div>
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

export default Design;
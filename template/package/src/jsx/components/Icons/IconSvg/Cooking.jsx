import React,{useReducer} from 'react';
import {Link} from 'react-router-dom';
import { Modal } from 'react-bootstrap';


import { ICONS } from '../../../constant/theme';

const svgBlogData = [
    {Iconname : 'Baking-glove.svg', svgtype : ICONS.BakingGlove},
    {Iconname : 'Bowl.svg', svgtype : ICONS.Bowl},
    {Iconname : 'Chef.svg', svgtype : ICONS.Chef},
    {Iconname : 'Cooking-Book.svg', svgtype : ICONS.CookingBook},
    {Iconname : 'Cooking-Pot.svg', svgtype : ICONS.CookingPot},
    {Iconname : 'Cutting-Board.svg', svgtype : ICONS.CuttingBoard},
    {Iconname : 'Dinner.svg', svgtype : ICONS.Dinner},
    {Iconname : 'Dish.svg', svgtype : ICONS.Dish},
    {Iconname : 'Dishes.svg', svgtype : ICONS.Dishes},
    {Iconname : 'Fork-Spoon-Knife.svg', svgtype : ICONS.ForkSpoonKnife},
    {Iconname : 'Fork-Spoon.svg', svgtype : ICONS.ForkSpoon},
    {Iconname : 'Fork.svg', svgtype : ICONS.Fork},
    {Iconname : 'Frying-Pan.svg', svgtype : ICONS.FryingPan},
    {Iconname : 'Grater.svg', svgtype : ICONS.Grater},
    {Iconname : 'Kitchen-Scale.svg', svgtype : ICONS.KitchenScale},
    {Iconname : 'Knife#1.svg', svgtype : ICONS.Knife_1},
    {Iconname : 'Knife#2.svg', svgtype : ICONS.Knife_2},
    {Iconname : 'Knife&fork#1.svg', svgtype : ICONS.Knife_fork_1},
    {Iconname : 'Knife&fork#2.svg', svgtype : ICONS.Knife_fork_2},
    {Iconname : 'Ladle.svg', svgtype : ICONS.Ladle},
    {Iconname : 'Rolling-Pin.svg', svgtype : ICONS.RollingPin},
    {Iconname : 'Saucepan.svg', svgtype : ICONS.Saucepan},
    {Iconname : 'Shovel.svg', svgtype : ICONS.Shovel},
    {Iconname : 'Sieve.svg', svgtype : ICONS.Sieve},
    {Iconname : 'Spoon.svg', svgtype : ICONS.Spoon},    
];

const Cooking = () => {
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
            <div className="card-header">Cooking</div>
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

export default Cooking;
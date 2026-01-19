import React,{useReducer} from 'react';
import {Link} from 'react-router-dom';
import { Modal } from 'react-bootstrap';


import { ICONS } from '../../../constant/theme';

const svgBlogData = [
    {Iconname : 'Beer.svg', svgtype : ICONS.Beer},
    {Iconname : 'Bottle#1.svg', svgtype : ICONS.Bottle1},
    {Iconname : 'Bottle#2.svg', svgtype : ICONS.Bottle2},
    {Iconname : 'Bread.svg', svgtype : ICONS.Bread},
    {Iconname : 'Bucket.svg', svgtype : ICONS.FoodBucket},
    {Iconname : 'Burger.svg', svgtype : ICONS.Burger},
    {Iconname : 'Cake.svg', svgtype : ICONS.Cake},
    {Iconname : 'Carrot.svg', svgtype : ICONS.Carrot},
    {Iconname : 'Cheese.svg', svgtype : ICONS.Cheese},
    {Iconname : 'Chicken.svg', svgtype : ICONS.Chicken},
    {Iconname : 'Coffee#1.svg', svgtype : ICONS.Coffee1},
    {Iconname : 'Coffee#2.svg', svgtype : ICONS.Coffee2},
    {Iconname : 'Cookie.svg', svgtype : ICONS.Cookie},
    {Iconname : 'Dinner.svg', svgtype : ICONS.FoodDinner},
    {Iconname : 'Fish.svg', svgtype : ICONS.Fish},
    {Iconname : 'French-Bread.svg', svgtype : ICONS.FrenchBread},
    {Iconname : 'Glass-Martini.svg', svgtype : ICONS.GlassMartini},
    {Iconname : 'IceCream#1.svg', svgtype : ICONS.IceCream1},
    {Iconname : 'IceCream#2.svg', svgtype : ICONS.IceCream2},
    {Iconname : 'Miso-Soup.svg', svgtype : ICONS.MisoSoup},
    {Iconname : 'Orange.svg', svgtype : ICONS.Orange},
    {Iconname : 'Pizza.svg', svgtype : ICONS.Pizza},
    {Iconname : 'Sushi.svg', svgtype : ICONS.Sushi},
    {Iconname : 'Two-Bottles.svg', svgtype : ICONS.TwoBottles},
    {Iconname : 'Wine.svg', svgtype : ICONS.Wine},

    //{Iconname : '.svg', svgtype : ICONS.},
    
];

const Food = () => {
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
            <div className="card-header">Food</div>
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

export default Food;
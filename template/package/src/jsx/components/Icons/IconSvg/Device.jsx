import React,{useReducer} from 'react';
import {Link} from 'react-router-dom';
import { Modal } from 'react-bootstrap';


import { ICONS } from '../../../constant/theme';

const svgBlogData = [
    {Iconname : 'Airpods.svg', svgtype : ICONS.Airpods},
    {Iconname : 'Android.svg', svgtype : ICONS.Android},
    {Iconname : 'Apple-Watch.svg', svgtype : ICONS.AppleWatch},
    {Iconname : 'Battery-Charging.svg', svgtype : ICONS.BatteryCharging},
    {Iconname : 'Battery-Empty.svg', svgtype : ICONS.BatteryEmpty},
    {Iconname : 'Battery-Full.svg', svgtype : ICONS.BatteryFull},
    {Iconname : 'Battery-Half.svg', svgtype : ICONS.BatteryHalf},
    {Iconname : 'Bluetooth.svg', svgtype : ICONS.Bluetooth},
    {Iconname : 'Camera.svg', svgtype : ICONS.Camera},
    {Iconname : 'Cardboard-Vr.svg', svgtype : ICONS.CardboardVr},
    {Iconname : 'Cassete.svg', svgtype : ICONS.Cassete},
    {Iconname : 'CPU1.svg', svgtype : ICONS.CPU1},
    {Iconname : 'CPU2.svg', svgtype : ICONS.CPU2},
    {Iconname : 'Diagnostics.svg', svgtype : ICONS.Diagnostics},
    {Iconname : 'Display-1.svg', svgtype : ICONS.Display1},
    {Iconname : 'Display-2.svg', svgtype : ICONS.Display2},
    {Iconname : 'Display-3.svg', svgtype : ICONS.Display3},
    {Iconname : 'Gameboy.svg', svgtype : ICONS.Gameboy},
    {Iconname : 'Gamepad-1.svg', svgtype : ICONS.Gamepad1},
    {Iconname : 'Gamepad-2.svg', svgtype : ICONS.Gamepad2},
    {Iconname : 'Generator.svg', svgtype : ICONS.Generator},
    {Iconname : 'Hard-Drive.svg', svgtype : ICONS.HardDrive},
    {Iconname : 'Headphones.svg', svgtype : ICONS.Headphones},
    {Iconname : 'Homepod.svg', svgtype : ICONS.Homepod},
    {Iconname : 'iMac.svg', svgtype : ICONS.iMac},
    {Iconname : 'iPhone-Back.svg', svgtype : ICONS.iPhoneBack},
    {Iconname : 'iPhone-X-Back.svg', svgtype : ICONS.iPhoneXBack},
    {Iconname : 'iPhone-X.svg', svgtype : ICONS.iPhoneX},
    {Iconname : 'Keyboard.svg', svgtype : ICONS.Keyboard},
    {Iconname : 'Laptop-Macbook.svg', svgtype : ICONS.LaptopMacbook},
    {Iconname : 'Laptop.svg', svgtype : ICONS.Laptop},
    {Iconname : 'LTE-1.svg', svgtype : ICONS.LTE1},
    {Iconname : 'LTE-2.svg', svgtype : ICONS.LTE2},
    {Iconname : 'Mic.svg', svgtype : ICONS.Mic},
    {Iconname : 'Midi.svg', svgtype : ICONS.Midi},
    {Iconname : 'Mouse.svg', svgtype : ICONS.Mouse},
    {Iconname : 'Phone.svg', svgtype : ICONS.Phone},
    {Iconname : 'Printer.svg', svgtype : ICONS.Printer},
    {Iconname : 'Radio.svg', svgtype : ICONS.Radio},
    {Iconname : 'Router-1.svg', svgtype : ICONS.Router1},
    {Iconname : 'Router-2.svg', svgtype : ICONS.Router2},
    {Iconname : 'SD-Card.svg', svgtype : ICONS.SDCard},
    {Iconname : 'Server.svg', svgtype : ICONS.Server},
    {Iconname : 'Speaker.svg', svgtype : ICONS.Speaker},
    {Iconname : 'Tablet.svg', svgtype : ICONS.Tablet},
    {Iconname : 'TV-1.svg', svgtype : ICONS.TV1},
    {Iconname : 'Usb-Storage.svg', svgtype : ICONS.TV2},
    {Iconname : 'USB.svg', svgtype : ICONS.USB},
    {Iconname : 'Video-Camera.svg', svgtype : ICONS.VideoCamera},
    {Iconname : 'Watch_1.svg', svgtype : ICONS.Watch_1},
    {Iconname : 'Watch_2.svg', svgtype : ICONS.Watch_2},
    {Iconname : 'Wi-Fi.svg', svgtype : ICONS.WiFi},
     
];

const Device = () => {
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
            <div className="card-header">Devices</div>
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

export default Device;
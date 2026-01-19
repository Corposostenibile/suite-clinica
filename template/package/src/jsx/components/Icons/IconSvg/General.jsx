import React,{useReducer} from 'react';
import {Link} from 'react-router-dom';
import { Modal } from 'react-bootstrap';


import { ICONS } from '../../../constant/theme';

const svgBlogData = [
    {
        title:"General",
        content : [
            {Iconname : 'Attachment#1.svg', svgtype : ICONS.Attachment1},    
            {Iconname : 'Attachment#2.svg', svgtype : ICONS.Attachment2},    
            {Iconname : 'Binocular.svg', svgtype : ICONS.Binocular},    
            {Iconname : 'Bookmark.svg', svgtype : ICONS.Bookmark},    
            {Iconname : 'Clip.svg', svgtype : ICONS.Clip},    
            {Iconname : 'Clipboard.svg', svgtype : ICONS.Clipboard},    
            {Iconname : 'Cursor.svg', svgtype : ICONS.Cursor},    
            {Iconname : 'Dislike.svg', svgtype : ICONS.Dislike},    
            {Iconname : 'Duplicate.svg', svgtype : ICONS.Duplicate},    
            {Iconname : 'Edit.svg', svgtype : ICONS.GeneralEdit},  
            {Iconname : 'Expand-Arrows.svg', svgtype : ICONS.ExpandArrows},  
            {Iconname : 'Fire.svg', svgtype : ICONS.Fire},  
            {Iconname : 'Folder.svg', svgtype : ICONS.GeneralFolder},  
            {Iconname : 'Half Heart.svg', svgtype : ICONS.HalfHeart},  
            {Iconname : 'Half Star.svg', svgtype : ICONS.HalfStar},  
            {Iconname : 'Heart.svg', svgtype : ICONS.Heart},  
            {Iconname : 'Hidden.svg', svgtype : ICONS.Hidden},  
            {Iconname : 'Like.svg', svgtype : ICONS.Like},  
            {Iconname : 'Lock.svg', svgtype : ICONS.Lock},  
            {Iconname : 'Notification#2.svg', svgtype : ICONS.Notification2},  
            {Iconname : 'Notification#1.svg', svgtype : ICONS.Notification1},  
            {Iconname : 'Other#1.svg', svgtype : ICONS.Other1},  
            {Iconname : 'Other#2.svg', svgtype : ICONS.Other2},  
            {Iconname : 'Sad.svg', svgtype : ICONS.Sad},  
            {Iconname : 'Save.svg', svgtype : ICONS.Save},  
            {Iconname : 'Scale.svg', svgtype : ICONS.Scale},  
            {Iconname : 'Scissors.svg', svgtype : ICONS.Scissors},  
            {Iconname : 'Search.svg', svgtype : ICONS.Search},  
        ],
    },
    {
        title:"Home",
        content : [
            {Iconname : 'Air-Ballon.svg', svgtype : ICONS.AirBallon},     
            {Iconname : 'Alarm-Clock.svg', svgtype : ICONS.AlarmClock},     
            {Iconname : 'Armchair.svg', svgtype : ICONS.Armchair},     
            {Iconname : 'Bag-Chair.svg', svgtype : ICONS.BagChair},     
            {Iconname : 'Bath.svg', svgtype : ICONS.Bath},     
            {Iconname : 'Bed.svg', svgtype : ICONS.Bed},     
            {Iconname : 'Bulb#2.svg', svgtype : ICONS.Bulb2},     
            {Iconname : 'Chair#1.svg', svgtype : ICONS.Chair1},     
            {Iconname : 'Chair#2.svg', svgtype : ICONS.Chair2},     
            {Iconname : 'Clock.svg', svgtype : ICONS.Clock},     
            {Iconname : 'Commode#1.svg', svgtype : ICONS.Commode1},     
            {Iconname : 'Commode#2.svg', svgtype : ICONS.Commode2},     
            {Iconname : 'Couch.svg', svgtype : ICONS.Couch},     
            {Iconname : 'Cupboard.svg', svgtype : ICONS.Cupboard},     
            {Iconname : 'Curtains.svg', svgtype : ICONS.Curtains},     
            {Iconname : 'Deer.svg', svgtype : ICONS.Deer},     
            {Iconname : 'DoorOpen.svg', svgtype : ICONS.DoorOpen},     
            {Iconname : 'Earth.svg', svgtype : ICONS.Earth},     
            {Iconname : 'Fireplace.svg', svgtype : ICONS.Fireplace},     
            {Iconname : 'Flashlight.svg', svgtype : ICONS.Flashlight},     
            {Iconname : 'Flower#1.svg', svgtype : ICONS.Flower1},     
            {Iconname : 'Flower#2.svg', svgtype : ICONS.Flower2},     
            {Iconname : 'Flower#3.svg', svgtype : ICONS.Flower3},     
            {Iconname : 'Globe.svg', svgtype : ICONS.Globe},     
            {Iconname : 'Home-Heart.svg', svgtype : ICONS.HomeHeart},     
            {Iconname : 'Home.svg', svgtype : ICONS.HomeIcon},     
            {Iconname : 'Key.svg', svgtype : ICONS.Key},     
            {Iconname : 'Ladder.svg', svgtype : ICONS.Ladder},     
            {Iconname : 'Lamp1.svg', svgtype : ICONS.Lamp1},     
            {Iconname : 'Lamp2.svg', svgtype : ICONS.Lamp2},     
            {Iconname : 'Library.svg', svgtype : ICONS.Library},     
            {Iconname : 'Mailbox.svg', svgtype : ICONS.Mailbox},     
            {Iconname : 'Mirror.svg', svgtype : ICONS.Mirror},     
            {Iconname : 'Picture.svg', svgtype : ICONS.Picture},     
            {Iconname : 'Ruller.svg', svgtype : ICONS.Ruller},     
            {Iconname : 'Stairs.svg', svgtype : ICONS.Stairs},     
            {Iconname : 'Timer.svg', svgtype : ICONS.Timer},     
            {Iconname : 'Toilet.svg', svgtype : ICONS.Toilet},     
            {Iconname : 'Towel.svg', svgtype : ICONS.Towel},     
            {Iconname : 'Trash.svg', svgtype : ICONS.Trash},     
            {Iconname : 'Water-Mixer.svg', svgtype : ICONS.WaterMixer},     
            {Iconname : 'Weight#1.svg', svgtype : ICONS.Weight1},                             
            {Iconname : 'Weight#2.svg', svgtype : ICONS.Weight2},     
            {Iconname : 'Wood#1.svg', svgtype : ICONS.Wood1},     
            {Iconname : 'Wood#2.svg', svgtype : ICONS.Wood2},     
            {Iconname : 'Wood-Horse.svg', svgtype : ICONS.WoodHorse},     
            
        ],
    },
    {
        title:"Layout",
        content : [
            {Iconname : 'Layout-3d.svg', svgtype : ICONS.Layout3d},    
            {Iconname : 'Layout-4b-locks.svg', svgtype : ICONS.Layout4blocks},    
            {Iconname : 'Layout-arrange.svg', svgtype : ICONS.LayoutArrange},    
            {Iconname : 'Layout-grid.svg', svgtype : ICONS.Layoutgrid},    
            {Iconname : 'Layout-horizontal.svg', svgtype : ICONS.Layouthorizontal},    
            {Iconname : 'Layout-left-panel-1.svg', svgtype : ICONS.Layoutleftpanel1},    
            {Iconname : 'Layout-left-panel-2.svg', svgtype : ICONS.Layoutleftpanel2},    
            {Iconname : 'Layout-right-panel-1.svg', svgtype : ICONS.Layoutrightpanel1},    
            {Iconname : 'Layout-right-panel-2.svg', svgtype : ICONS.Layoutrightpanel2},    
            {Iconname : 'Layout-top-panel-1.svg', svgtype : ICONS.Layouttoppanel1},    
            {Iconname : 'Layout-top-panel-2.svg', svgtype : ICONS.Layouttoppanel2},    
            {Iconname : 'Layout-top-panel-3.svg', svgtype : ICONS.Layouttoppanel3},    
            {Iconname : 'Layout-top-panel-4.svg', svgtype : ICONS.Layouttoppanel4},    
            {Iconname : 'Layout-top-panel-5.svg', svgtype : ICONS.Layouttoppanel5},    
            {Iconname : 'Layout-top-panel-6.svg', svgtype : ICONS.Layouttoppanel6},    
            {Iconname : 'Layout-vertical.svg', svgtype : ICONS.Layoutvertical},    
        ]
    },
    {
        title:"Map",
        content : [
            {Iconname : 'Compass.svg', svgtype : ICONS.MapCompass},  
            {Iconname : 'Direction#1.svg', svgtype : ICONS.Direction1},  
            {Iconname : 'Direction#2.svg', svgtype : ICONS.Direction2},  
            {Iconname : 'Location-arrow.svg', svgtype : ICONS.Locationarrow},  
            {Iconname : 'Marker#1.svg', svgtype : ICONS.Marker1},  
            {Iconname : 'Marker#2.svg', svgtype : ICONS.Marker2},  
            {Iconname : 'Position.svg', svgtype : ICONS.MapPosition},  
        ]
    },
    {
        title:"Media",
        content : [
            {Iconname : 'Add-music.svg', svgtype : ICONS.Addmusic},  
            {Iconname : 'Airplay-video.svg', svgtype : ICONS.Airplayvideo},  
            {Iconname : 'Airplay.svg', svgtype : ICONS.Airplay},  
            {Iconname : 'Back.svg', svgtype : ICONS.Back},  
            {Iconname : 'Backward.svg', svgtype : ICONS.Backward},  
            {Iconname : 'CD.svg', svgtype : ICONS.CD},  
            {Iconname : 'DVD.svg', svgtype : ICONS.DVD},  
            {Iconname : 'Eject.svg', svgtype : ICONS.Eject},  
            {Iconname : 'Equalizer.svg', svgtype : ICONS.Equalizer},  
            {Iconname : 'Forward.svg', svgtype : ICONS.MediaForward},  
            {Iconname : 'Media-library#1.svg', svgtype : ICONS.Medialibrary1},  
            {Iconname : 'Media-library#2.svg', svgtype : ICONS.Medialibrary2},  
            {Iconname : 'Media-library#3.svg', svgtype : ICONS.Medialibrary3},  
            {Iconname : 'Movie-Lane #2.svg', svgtype : ICONS.MovieLane2},  
            {Iconname : 'Movie-lane#1.svg', svgtype : ICONS.Movielane1},  
            {Iconname : 'Music-cloud.svg', svgtype : ICONS.Musiccloud},  
            {Iconname : 'Music-note.svg', svgtype : ICONS.Musicnote},  
            {Iconname : 'Music.svg', svgtype : ICONS.Music},  
        ]
    },
    {
        title:"Navigation",
        content : [
            {Iconname : 'Angle-double-down.svg', svgtype : ICONS.Angledoubledown},
            {Iconname : 'Angle-double-left.svg', svgtype : ICONS.Angledoubleleft},
            {Iconname : 'Angle-double-right.svg', svgtype : ICONS.Angledoubleright},
            {Iconname : 'Angle-double-up.svg', svgtype : ICONS.Angledoubleup},
            {Iconname : 'Angle-down.svg', svgtype : ICONS.Angledown},
            {Iconname : 'Angle-left.svg', svgtype : ICONS.Angleleft},
            {Iconname : 'Angle-right.svg', svgtype : ICONS.Angleright},
            {Iconname : 'Arrow-down.svg', svgtype : ICONS.Arrowdown},
            {Iconname : 'Arrow-from-bottom.svg', svgtype : ICONS.Arrowfrombottom},
            {Iconname : 'Arrow-from-left.svg', svgtype : ICONS.Arrowfromleft},
            {Iconname : 'Arrow-from-right.svg', svgtype : ICONS.Arrowfromright},
            {Iconname : 'Arrow-from-top.svg', svgtype : ICONS.Arrowfromtop},
            {Iconname : 'Arrow-left.svg', svgtype : ICONS.Arrowleft},
            {Iconname : 'Arrow-right.svg', svgtype : ICONS.Arrowright},
            {Iconname : 'Arrow-to-bottom.svg', svgtype : ICONS.Arrowtobottom},
            {Iconname : 'Arrow-to-left.svg', svgtype : ICONS.Arrowtoleft},
            {Iconname : 'Arrow-to-right.svg', svgtype : ICONS.Arrowtoright},
            {Iconname : 'Arrow-to-up.svg', svgtype : ICONS.Arrowtoup},
            {Iconname : 'Arrow-up.svg', svgtype : ICONS.Arrowup},
            {Iconname : 'Arrows-h.svg', svgtype : ICONS.Arrowsh},
            {Iconname : 'Arrows-v.svg', svgtype : ICONS.Arrowsv},
            {Iconname : 'Check.svg', svgtype : ICONS.Check},
            {Iconname : 'Close.svg', svgtype : ICONS.Close},
            {Iconname : 'Double-check.svg', svgtype : ICONS.Doublecheck},
        ]
    },
    {
        title:"Shopping",
        content : [
            {Iconname : 'ATM.svg', svgtype : ICONS.ATM},
            {Iconname : 'Bag#1.svg', svgtype : ICONS.Bag1},
            {Iconname : 'Bag#2 .svg', svgtype : ICONS.Bag2},
            {Iconname : 'Barcode-read.svg', svgtype : ICONS.Barcoderead},
            {Iconname : 'Barcode-scan.svg', svgtype : ICONS.Barcodescan},
            {Iconname : 'Barcode.svg', svgtype : ICONS.Barcode},
            {Iconname : 'Bitcoin.svg', svgtype : ICONS.Bitcoin},
            {Iconname : 'Box#1.svg', svgtype : ICONS.Box1},
            {Iconname : 'Box#2.svg', svgtype : ICONS.Box2},
            {Iconname : 'Box#3.svg', svgtype : ICONS.Box3},
            {Iconname : 'Calculator.svg', svgtype : ICONS.Calculator},
            {Iconname : 'Cart#1 .svg', svgtype : ICONS.Cart1},
            {Iconname : 'Cart#2.svg', svgtype : ICONS.Cart2},
            {Iconname : 'Cart#3.svg', svgtype : ICONS.Cart3},
            {Iconname : 'Chart-bar#1.svg', svgtype : ICONS.Chartbar1},
            {Iconname : 'Chart-bar#2.svg', svgtype : ICONS.Chartbar2},
            {Iconname : 'Chart-bar#3.svg', svgtype : ICONS.Chartbar3},
            {Iconname : 'Chart-line#1.svg', svgtype : ICONS.Chartline1},
            {Iconname : 'Chart-line#2.svg', svgtype : ICONS.Chartline2},
            {Iconname : 'Chart-pie.svg', svgtype : ICONS.Chartpie},
            {Iconname : 'Credit-card.svg', svgtype : ICONS.Creditcard},
            {Iconname : 'Dollar.svg', svgtype : ICONS.Dollar},
            {Iconname : 'Euro.svg', svgtype : ICONS.Euro},
            {Iconname : 'Gift.svg', svgtype : ICONS.Gift},
        ]
    },
    {
        title:"Text",
        content : [
            {Iconname : 'Align-auto.svg', svgtype : ICONS.Alignauto},
            {Iconname : 'Align-center.svg', svgtype : ICONS.Aligncenter},
            {Iconname : 'Align-justify.svg', svgtype : ICONS.Alignjustify},
            {Iconname : 'Align-left.svg', svgtype : ICONS.Alignleft},
            {Iconname : 'Align-right.svg', svgtype : ICONS.Alignright},
            {Iconname : 'Article.svg', svgtype : ICONS.Article},
            {Iconname : 'Bold.svg', svgtype : ICONS.Bold},
            {Iconname : 'Bullet-list.svg', svgtype : ICONS.Bulletlist},
            {Iconname : 'Code.svg', svgtype : ICONS.TextCode},
            {Iconname : 'dit-text.svg', svgtype : ICONS.Edittext},
            {Iconname : 'Filter.svg', svgtype : ICONS.Filter},
            {Iconname : 'Font.svg', svgtype : ICONS.Font},
            {Iconname : 'H1.svg', svgtype : ICONS.H1},
            {Iconname : 'H2.svg', svgtype : ICONS.H2},
            {Iconname : 'Itallic.svg', svgtype : ICONS.Itallic},
            {Iconname : 'Menu.svg', svgtype : ICONS.Menu},
            {Iconname : 'Paragraph.svg', svgtype : ICONS.Paragraph},
            {Iconname : 'Quote#1.svg', svgtype : ICONS.Quote1},
            {Iconname : 'Quote#2.svg', svgtype : ICONS.Quote2},
            {Iconname : 'Redo.svg', svgtype : ICONS.Redo},
            {Iconname : 'Strikethrough.svg', svgtype : ICONS.Strikethrough},
            {Iconname : 'Text-height.svg', svgtype : ICONS.Textheight},
            {Iconname : 'Text-width.svg', svgtype : ICONS.Textwidth},
            {Iconname : 'Text.svg', svgtype : ICONS.Text},
            {Iconname : 'Underline.svg', svgtype : ICONS.Underline},
            {Iconname : 'Undo.svg', svgtype : ICONS.Undo},
        ]
    },
    {
        title:"Tools",
        content : [
            {Iconname : 'Angle Grinder.svg', svgtype : ICONS.AngleGrinder},
            {Iconname : 'Axe.svg', svgtype : ICONS.Axe},
            {Iconname : 'AxeBrush.svg', svgtype : ICONS.AxeBrush},
            {Iconname : 'Compass.svg', svgtype : ICONS.Compass},
            {Iconname : 'Hummer#2.svg', svgtype : ICONS.Hummer2},
            {Iconname : 'Hummer.svg', svgtype : ICONS.Hummer},
            {Iconname : 'Pantone.svg', svgtype : ICONS.Pantone},
            {Iconname : 'oad-Cone.svg', svgtype : ICONS.RoadCone},
            {Iconname : 'Roller.svg', svgtype : ICONS.Roller},
            {Iconname : 'Roulette.svg', svgtype : ICONS.Roulette},
            {Iconname : 'Screwdriver.svg', svgtype : ICONS.Screwdriver},
            {Iconname : 'Shovel.svg', svgtype : ICONS.ToolsShovel},
            {Iconname : 'Spatula.svg', svgtype : ICONS.Spatula},
            {Iconname : 'Swiss-knife.svg', svgtype : ICONS.Swissknife},
            {Iconname : 'Tools.svg', svgtype : ICONS.Tools},
        ]
    },
    {
        title:"Weather",
        content : [
            {Iconname : 'Celcium.svg', svgtype : ICONS.Celcium},
            {Iconname : 'Cloud#1.svg', svgtype : ICONS.Cloud1},
            {Iconname : 'Cloud#2.svg', svgtype : ICONS.Cloud2},
            {Iconname : 'Cloud-fog.svg', svgtype : ICONS.Cloudfog},
            {Iconname : 'Cloud-sun.svg', svgtype : ICONS.Cloudsun},
            {Iconname : 'Cloud-wind.svg', svgtype : ICONS.Cloudwind},
            {Iconname : 'Cloudy-night.svg', svgtype : ICONS.Cloudynight},
            {Iconname : 'Cloudy.svg', svgtype : ICONS.Cloudy},
            {Iconname : 'Day-rain.svg', svgtype : ICONS.Dayrain},
            {Iconname : 'Fahrenheit.svg', svgtype : ICONS.Fahrenheit},
            {Iconname : 'Fog.svg', svgtype : ICONS.Fog},
            {Iconname : 'Moon.svg', svgtype : ICONS.Moon},
            {Iconname : 'Night-fog.svg', svgtype : ICONS.Nightfog},
            {Iconname : 'Night-rain.svg', svgtype : ICONS.Nightrain},
            {Iconname : 'Rain#1.svg', svgtype : ICONS.Rain1},
            {Iconname : 'Rain#2.svg', svgtype : ICONS.Rain2},
            {Iconname : 'Rain#5.svg', svgtype : ICONS.Rain5},
            {Iconname : 'Rainbow.svg', svgtype : ICONS.Rainbow},
            {Iconname : 'Snow#1.svg', svgtype : ICONS.Snow1},
            {Iconname : 'Snow#2.svg', svgtype : ICONS.Snow2},
            {Iconname : 'Snow#3.svg', svgtype : ICONS.Snow3},
            {Iconname : 'Snow.svg', svgtype : ICONS.Snow},
            {Iconname : 'Storm.svg', svgtype : ICONS.Storm},
            {Iconname : 'Sun-fog.svg', svgtype : ICONS.Sunfog},
            {Iconname : 'Sun.svg', svgtype : ICONS.Sun},
            {Iconname : 'Suset#1.svg', svgtype : ICONS.Suset1},
            {Iconname : 'Suset#2.svg', svgtype : ICONS.Suset2},
            {Iconname : 'Temperature-empty.svg', svgtype : ICONS.Temperatureempty},
            {Iconname : 'Temperature-full.svg', svgtype : ICONS.Temperaturefull},
            {Iconname : 'Temperature-half.svg', svgtype : ICONS.Temperaturehalf},
            {Iconname : 'Thunder-night.svg', svgtype : ICONS.Thundernight},
            {Iconname : 'Thunder.svg', svgtype : ICONS.Thunder},
            {Iconname : 'Umbrella.svg', svgtype : ICONS.Umbrella},
            {Iconname : 'Wind.svg', svgtype : ICONS.Wind},
        ]
    },
];

const General = () => {
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
                {svgBlogData.map((data)=>(
                    <>
                        <div className="card-header">{data.title}</div>
                        <div className="row">							
                            {data.content && data.content.map((item, ind)=>(
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
                    </>
                ))}
                           
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

export default General;
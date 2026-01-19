import React, { Fragment, useState,useReducer } from "react";
import {Tab, Nav, Collapse} from 'react-bootstrap';
import {Link} from 'react-router-dom';

// import SideBar from "./SideBar";
import NavHeader2 from "./NavHeader2";
import Header from "./Header";
import ChatBox from "../ChatBox";

//Menus
import {MenuList2} from './Menus2'

//Images
import icon1 from './../../../images/browser/icon1.png';
import icon2 from './../../../images/browser/icon2.png';

import ShareProfitCanvas from './FixedData/ShareProfitCanvas';
import DailySalesCanvas from './FixedData/DailySalesCanvas';
//Icons
import { SVGICON } from "../../constant/theme";
import LogoutMini from "./LogoutMini";


const browserList = [
    {image: icon1, title:'Chrome', color:'warning', percent:'90%'},
    {image: icon2, title:'Firefox', color:'success', percent:'80%'},
    {image: icon1, title:'Chrome', color:'danger', percent:'70%'},
];

const sidebarMenu = [
    {mainicon: SVGICON.HomeIcon, menuKey:"Dashboard"},
    {mainicon: SVGICON.HomeIcon2, menuKey:"Dashboard1"},
    {mainicon: SVGICON.SettingIcon, menuKey:"Cms"},
    {mainicon: SVGICON.AppsIcon, menuKey:"Apps"},
    {mainicon: SVGICON.BootstrapIcon, menuKey:"Bootstrap"},
    {mainicon: SVGICON.FormIcon, menuKey:"Form"},
    {mainicon: SVGICON.TableIcon, menuKey:"Table"},
    {mainicon: SVGICON.PageIcon, menuKey:"Page"},
    // {mainicon: SVGICON.ShoppingIocn, menuKey:"Shopping"},    
];


const initialState = false;
const reducer = (state, action) =>{
    switch (action.type){
        case 'collpase0':
            return { ...state, collpase0: !state.collpase0 }
        case 'collpase1':
            return { ...state, collpase1: !state.collpase1 }
        case 'collpase2':
            return { ...state, collpase2: !state.collpase2 }
        case 'collpase3':
            return { ...state, collpase3: !state.collpase3 }
        default:
            return state;
    }
}

const updateReducer = (previousState, updatedState) => ({
    ...previousState,
    ...updatedState,
  });
  
const menuInitial = {
    active : "",
    activeSubmenu : "",
}

const Deflayout = ({ title, onClick: ClickToAddEvent }) => {
    const [toggle, setToggle] = useState("");
    const onClick = (name) => setToggle(toggle === name ? "" : name);

    const [activeMenu, setActiveMenu] = useState(0)
    const [state, dispatch] = useReducer(reducer, initialState);

    const [menustate, setMenustate] = useReducer(updateReducer, menuInitial);
    const handleMenuActive = status => {		
        setMenustate({active : status});			
        if(menustate.active === status){				
            setMenustate({active : ""});
        }   
    }
    const handleSubmenuActive = (status) => {		
        setMenustate({activeSubmenu : status})
        if(menustate.activeSubmenu === status){
            setMenustate({activeSubmenu : ""})			
        }    
    }


    const [openSidebar, setOpenSidebar] = useState(false);
    const [closeSidebar, setCloseSidebar] = useState(0);
        function handleMenuOpen(ind){
            if(ind=== closeSidebar){
                setOpenSidebar(!openSidebar);
            }
        }

  return (
    <Fragment>
      <NavHeader2 openSidebar={openSidebar} />
      <ChatBox onClick={() => onClick("chatbox")} toggle={toggle} />
      <Tab.Container defaultActiveKey={"Dashboard"}>
        <div className= {`fixed-content-box ${openSidebar ? "active" : ""}`}>
            <div className="head-name">
                MotaAdmin
                <span className="close-fixed-content fa-left d-lg-none"
                    onClick={()=>setOpenSidebar(false)}
                >
                    <svg xmlns="http://www.w3.org/2000/svg" width="24px" height="24px" viewBox="0 0 24 24" version="1.1">
                        <g stroke="none" strokeWidth="1" fill="none" fillRule="evenodd">
                        <polygon points="0 0 24 0 24 24 0 24"/>
                        <rect fill="#000000" opacity="0.3" transform="translate(15.000000, 12.000000) scale(-1, 1) rotate(-90.000000) translate(-15.000000, -12.000000) " x="14" y="7" width="2" height="10" rx="1"/><path d="M3.7071045,15.7071045 C3.3165802,16.0976288 2.68341522,16.0976288 2.29289093,15.7071045 C1.90236664,15.3165802 1.90236664,14.6834152 2.29289093,14.2928909 L8.29289093,8.29289093 C8.67146987,7.914312 9.28105631,7.90106637 9.67572234,8.26284357 L15.6757223,13.7628436 C16.0828413,14.136036 16.1103443,14.7686034 15.7371519,15.1757223 C15.3639594,15.5828413 14.7313921,15.6103443 14.3242731,15.2371519 L9.03007346,10.3841355 L3.7071045,15.7071045 Z" fill="#000000" fillRule="nonzero" transform="translate(9.000001, 11.999997) scale(-1, -1) rotate(90.000000) translate(-9.000001, -11.999997) "/></g>
                    </svg>
                </span>
            </div>
            <div className="fixed-content-body dz-scroll" id="DZ_W_Fixed_Contant">                
                <Tab.Content>    
                    {
                        MenuList2[activeMenu].classStyle !=="blank" ?        
                            <div className="tab-pane show active">
                                <ul className="metismenu tab-nav-menu">		                               
                                    <>                                        
                                        {
                                            MenuList2[activeMenu].name === "doubleArray" ? 
                                            <>
                                                <li className="nav-label">{MenuList2[activeMenu].title}</li>
                                                {MenuList2[activeMenu].mainArray.map((item, ind)=>(
                                                    <li key={ind} className={`${item.title === menustate.active ? "mm-active" : ""}`}>
                                                        <Link to={"#"} className="has-arrow"
                                                            onClick={() => {handleMenuActive(item.title)}}
                                                        >
                                                            {item.iconStyle}                                                            
                                                            <span className="nav-text">{item.title}</span>                                                            
                                                        </Link>
                                                        <Collapse in={menustate.active === item.title ? true :false}>
                                                            <ul>
                                                                {item?.content?.map((data, ind)=>{
                                                                    if(data.metisMenu==="has-menu"){
                                                                        return(                                                                        
                                                                            <li key={ind}>
                                                                                <Link to={"#"} className="has-arrow"
                                                                                    onClick={() => { handleSubmenuActive(data.title)}}
                                                                                >{data.title}</Link>
                                                                                <Collapse  in={menustate.activeSubmenu === data.title ? true :false}>
                                                                                    <ul>
                                                                                        {data?.content?.map((data, ind)=>(
                                                                                            <li key={ind}><Link to={data.to}>{data.title}</Link></li>  
                                                                                        ))}
                                                                                    </ul>
                                                                                </Collapse>
                                                                            </li>
                                                                        )
                                                                    }else{
                                                                        return(                                                                           
                                                                            <li key={ind}><Link to={data.to}>{data.title}</Link></li>                                                                              
                                                                        )
                                                                    }
                                                                })}                                                                
                                                            </ul>
                                                        </Collapse>
                                                    </li>
                                                ))}
                                                
                                            </>
                                            :
                                            <>
                                                <li className="nav-label">{MenuList2[activeMenu].title}</li> 
                                                <li className={`${state.collpase1 ? "mm-active" : ""}`}>
                                                    <Link to={"#"} className="has-arrow" 
                                                        onClick={() => dispatch({type:'collpase1'})}
                                                    >   
                                                        {MenuList2[activeMenu]?.iconStyle}{" "}
                                                        <span className="nav-text">{MenuList2[activeMenu]?.title}</span>
                                                        {/* <span className="badge badge-xs badge-light">10</span> */}
                                                    </Link>
                                                    <Collapse in={state.collpase1}>
                                                        <ul>                                            
                                                            {MenuList2[activeMenu]?.content.map((data, ind)=>(                                                               
                                                                <li key={ind}>
                                                                    <Link to={data?.to}>{data?.title}</Link>                                                            
                                                                    <ul>
                                                                        {data?.content?.map((item,i) => (
                                                                            <li key={i}><Link to={item.to}>{item.title}</Link></li>
                                                                        ))}                                                                
                                                                    </ul>
                                                                </li> 
                                                            ))}

                                                        </ul>   
                                                    </Collapse>                                          
                                                </li>
                                            </>                                                                            
                                        }
                                    </>    
                                </ul>
                            </div>    
                            :
                            ""
                    }
                    <div className="tab-pane chart-sidebar fade show active" role="tabpanel">
                        <div className="card">
                            <div className="card-header align-items-start">
                                <div>
                                    <h6>Daily Sales</h6>
                                    <p>Check out each colum for more details</p>
                                </div>
                                <span className="btn btn-primary light sharp ml-2">
                                    <svg xmlns="http://www.w3.org/2000/svg" width="20px" height="20px" viewBox="0 0 24 24" version="1.1"><g stroke="none" strokeWidth="1" fill="none" fillRule="evenodd"><rect x="0" y="0" width="24" height="24"/><rect fill="#000000" opacity="0.3" x="12" y="4" width="3" height="13" rx="1.5"/><rect fill="#000000" opacity="0.3" x="7" y="9" width="3" height="8" rx="1.5"/><path d="M5,19 L20,19 C20.5522847,19 21,19.4477153 21,20 C21,20.5522847 20.5522847,21 20,21 L4,21 C3.44771525,21 3,20.5522847 3,20 L3,4 C3,3.44771525 3.44771525,3 4,3 C4.55228475,3 5,3.44771525 5,4 L5,19 Z" fill="#000000" fillRule="nonzero"/><rect fill="#000000" opacity="0.3" x="17" y="11" width="3" height="6" rx="1.5"/></g></svg>
                                </span>
                            </div>
                            <div className="card-body">                                
                                <DailySalesCanvas />
                            </div>
                        </div>
                        <div className="card bg-warning-light">
                            <div className="card-header align-items-start mb-3">
                                <div>
                                    <h6>Profit Share</h6>
                                    <p>Check out each colum for more details</p>
                                </div>
                                <span className="btn btn-warning light sharp ml-2">
                                    <svg xmlns="http://www.w3.org/2000/svg"  width="20px" height="20px" viewBox="0 0 24 24" version="1.1"><g stroke="none" strokeWidth="1" fill="none" fillRule="evenodd"><rect x="0" y="0" width="24" height="24"/><path d="M4.00246329,12.2004927 L13,14 L13,4.06189375 C16.9463116,4.55399184 20,7.92038235 20,12 C20,16.418278 16.418278,20 12,20 C7.64874861,20 4.10886412,16.5261253 4.00246329,12.2004927 Z" fill="#000000" opacity="0.3"/><path d="M3.0603968,10.0120794 C3.54712466,6.05992157 6.91622084,3 11,3 L11,11.6 L3.0603968,10.0120794 Z" fill="#000000"/></g></svg>
                                </span>
                            </div>
                            <div className="card-body">
                                <div className="chart-point">
                                    <div className="check-point-area">                                    
                                        <ShareProfitCanvas />
                                    </div>
                                    <ul className="chart-point-list">
                                        <li><i className="fa fa-circle text-primary mr-1"></i> 40% Tickets</li>
                                        <li><i className="fa fa-circle text-success mr-1"></i> 35% Events</li>
                                        <li><i className="fa fa-circle text-warning mr-1"></i> 25% Other</li>
                                    </ul>
                                </div>
                            </div>
                        </div>
                        <div className="card bg-info-light">
                            <div className="card-header align-items-start mb-3">
                                <div>
                                    <h6>Visitors By Browser</h6>
                                    <p>Check out each colum for more details</p>
                                </div>
                                <span className="btn btn-info light sharp ml-2">
                                    <svg xmlns="http://www.w3.org/2000/svg"  width="20px" height="20px" viewBox="0 0 24 24" version="1.1"><g stroke="none" strokeWidth="1" fill="none" fillRule="evenodd"><rect x="0" y="0" width="24" height="24"/><path d="M3,4 L20,4 C20.5522847,4 21,4.44771525 21,5 L21,7 C21,7.55228475 20.5522847,8 20,8 L3,8 C2.44771525,8 2,7.55228475 2,7 L2,5 C2,4.44771525 2.44771525,4 3,4 Z M10,10 L20,10 C20.5522847,10 21,10.4477153 21,11 L21,19 C21,19.5522847 20.5522847,20 20,20 L10,20 C9.44771525,20 9,19.5522847 9,19 L9,11 C9,10.4477153 9.44771525,10 10,10 Z" fill="#000000"/><rect fill="#000000" opacity="0.3" x="2" y="10" width="5" height="10" rx="1"/></g></svg>
                                </span>
                            </div>
                            <div className="card-body">
                                {browserList.map((data, ind)=>(
                                    <Fragment key={ind}>
                                        <p className="mb-2 d-flex">
                                            <img width="22" height="22" src={data.image} className="me-2" alt=""/>{data.title}
                                            <span className={`pull-right ms-auto text-${data.color}`}>{data.percent}</span>
                                        </p>
                                        <div className="progress mb-3" style={{height:"4px"}}>
                                            <div className={`progress-bar progress-animated bg-${data.color}`} style={{width: data.percent, height:"4px"}}>
                                                {/* <span className="sr-only">{data.percent} Complete</span> */}
                                            </div>
                                        </div>
                                    </Fragment>
                                ))}
                            
                            </div>
                        </div>
                    </div>
                </Tab.Content>
                
            </div>
        </div>
        <Header
            onNote={() => onClick("chatbox")}
            onNotification={() => onClick("notification")}
            onProfile={() => onClick("profile")}
            toggle={toggle}
            title={title}
            onBox={() => onClick("box")}
            onClick={() => ClickToAddEvent()}
        />
        {/* <SideBar /> */}
            <div className="deznav">
                <div className="deznav-scroll">
                    <Nav as="ul" className="nav menu-tabs"  >
                        {sidebarMenu.map((item, index)=>(
                            <Nav.Item as="li" key={index}                                
                                onClick={()=>{
                                    setOpenSidebar(true)
                                    handleMenuOpen(index)
                                    setCloseSidebar(index)
                                }}
                                
                            >
                                <Nav.Link className="ai-icon" eventKey={item.menuKey}
                                    onClick={()=>{
                                        setActiveMenu(index)                                                                            
                                    }}
                                >
                                    {item.mainicon}
                                </Nav.Link>
                            </Nav.Item>
                        ))}
                    </Nav>
                </div>
                <LogoutMini />
            </div>
        </Tab.Container>
    </Fragment>
  );
};

export default Deflayout;

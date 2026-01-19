import React, { Fragment, useState,useReducer } from "react";
import {Tab, Nav, Collapse} from 'react-bootstrap';
import {Link} from 'react-router-dom';

// import SideBar from "./SideBar";
import NavHader from "./NavHader";
import Header from "./Header";
import ChatBox from "../ChatBox";

//Menus
import {MenuList2} from './Menus2'
import {componentArray} from './Menus2'
//Images
import icon1 from './../../../images/browser/icon1.png';
import icon2 from './../../../images/browser/icon2.png';

import ShareProfitCanvas from './FixedData/ShareProfitCanvas';
import DailySalesCanvas from './FixedData/DailySalesCanvas';
//Icons
import { SVGICON } from "../../constant/theme";


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
    {mainicon: SVGICON.ShoppingIocn, menuKey:"Shopping"},    
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
    }
}

const updateReducer = (previousState, updatedState) => ({
    ...previousState,
    ...updatedState,
  });
  
const menuInitial = {
    active : "",
    // activeSubmenu : "",
}

const Deflayout = ({ title, onClick: ClickToAddEvent }) => {
  const [toggle, setToggle] = useState("");
  const onClick = (name) => setToggle(toggle === name ? "" : name);

    // const [number, setNumber] = useState(0);
    // const  [data, setData]  = useState(MenuList2[0]);
    const [activeMenu, setActiveMenu] = useState(0)

    const [state, dispatch] = useReducer(reducer, initialState);

    const [menustate, setMenustate] = useReducer(updateReducer, menuInitial);
    const handleMenuActive = status => {		
        setMenustate({active : status});			
        if(menustate.active === status){				
            setMenustate({active : ""});
        }   
    }
  return (
    <Fragment>
      <NavHader />
      <ChatBox onClick={() => onClick("chatbox")} toggle={toggle} />
      <Tab.Container defaultActiveKey={"Dashboard"}>
        <div className="fixed-content-box">
            <div className="head-name">
                MotaAdmin
                <span className="close-fixed-content fa-left d-lg-none">
                    <svg xmlns="http://www.w3.org/2000/svg" width="24px" height="24px" viewBox="0 0 24 24" version="1.1">
                        <g stroke="none" strokeWidth="1" fill="none" fillRule="evenodd">
                        <polygon points="0 0 24 0 24 24 0 24"/>
                        <rect fill="#000000" opacity="0.3" transform="translate(15.000000, 12.000000) scale(-1, 1) rotate(-90.000000) translate(-15.000000, -12.000000) " x="14" y="7" width="2" height="10" rx="1"/><path d="M3.7071045,15.7071045 C3.3165802,16.0976288 2.68341522,16.0976288 2.29289093,15.7071045 C1.90236664,15.3165802 1.90236664,14.6834152 2.29289093,14.2928909 L8.29289093,8.29289093 C8.67146987,7.914312 9.28105631,7.90106637 9.67572234,8.26284357 L15.6757223,13.7628436 C16.0828413,14.136036 16.1103443,14.7686034 15.7371519,15.1757223 C15.3639594,15.5828413 14.7313921,15.6103443 14.3242731,15.2371519 L9.03007346,10.3841355 L3.7071045,15.7071045 Z" fill="#000000" fillRule="nonzero" transform="translate(9.000001, 11.999997) scale(-1, -1) rotate(90.000000) translate(-9.000001, -11.999997) "/></g>
                    </svg>
                </span>
            </div>
            <div className="fixed-content-body dz-scroll" id="DZ_W_Fixed_Contant">
                
                    <Tab.Content>
                        {/* <Tab.Pane eventKey={"Dashboard"}></Tab.Pane> */}                        
                        <Tab.Pane eventKey="Dashboard1">
                            <ul className="metismenu tab-nav-menu">
                                <li className="nav-label">Dashboard</li>
                                <li className={`${state.collpase0 ? "mm-active" : ""}`}>
                                    <Link to={"#"} className="has-arrow"
                                        onClick={() => dispatch({type:'collpase0'})}
                                    >
                                        {SVGICON.Dashboard}
                                        {" "}Dashboard
                                    </Link>
                                    <Collapse in={state.collpase0}>
                                        <ul aria-expanded="false">
                                            <li><Link to={"/dashboard"}>Light</Link></li>
                                            <li><Link to={"/dashboard-dark"}>Dark</Link></li>
                                            <li><Link to={"/index-3"}>Mini Sidebar</Link></li>
                                            <li><Link to={"/index-4"}>Sidebar</Link></li>
                                        </ul>
                                    </Collapse>
                                </li>
                            </ul>
                        </Tab.Pane>
                        <Tab.Pane eventKey="Cms">
                            <ul className="metismenu tab-nav-menu">
                                <li className="nav-label">CMS</li>
                                <li className={`${state.collpase1 ? "mm-active" : ""}`}>
                                    <Link to={"#"} className="has-arrow"
                                        onClick={() => dispatch({type:'collpase1'})}
                                    >
                                        {SVGICON.CmsSvg}
                                        {" "}CMS                                    
                                    </Link>
                                    <Collapse in={state.collpase1}>
                                        <ul>
                                            <li><Link to={"/content"}>Content</Link></li>
                                            <li><Link to={"/menu"}>Menu</Link></li>
                                            <li><Link to={"/email-template"}>Email Template</Link></li>
                                            <li><Link to={"/blog"}>Blog</Link></li>
                                        </ul>
                                    </Collapse>
                                </li>
                            </ul>
                        </Tab.Pane>
                        <Tab.Pane eventKey={"Apps"}>
                            <ul className="metismenu tab-nav-menu">
                                <li className="nav-label">APPS</li>
                                <li>
                                    <Link to={"#"} className="has-arrow">
                                        {SVGICON.AppSvg}
                                        <span className="nav-text">Apps</span>
                                        <span className="badge badge-xs badge-light">10</span>
                                    </Link>
                                    <ul>
                                        <li><Link to={"/app-profile"}>Profile</Link></li>
                                        <li><Link to={"#"} className="has-arrow" >Email</Link>
                                            <ul>
                                                <li><Link to={"/email-compose"}>Compose</Link></li>
                                                <li><Link to={"/email-inbox"}>Inbox</Link></li>
                                                <li><Link to={"/email-read"}>Read</Link></li>
                                            </ul>
                                        </li>
                                        <li><Link to={"/app-calender"}>Calendar</Link></li>
                                        <li><Link to={"#"} className="has-arrow">Shop</Link>
                                            <ul>
                                                <li><Link to={"/ecom-product-grid"}>Product Grid</Link></li>
                                                <li><Link to={"/ecom-product-list"}>Product List</Link></li>
                                                <li><Link to={"/ecom-product-detail"}>Product Details</Link></li>
                                                <li><Link to={"/ecom-product-order"}>Order</Link></li>
                                                <li><Link to={"/ecom-checkout"}>Checkout</Link></li>
                                                <li><Link to={"/ecom-invoice"}>Invoice</Link></li>
                                                <li><Link to={"/ecom-customers"}>Customers</Link></li>
                                            </ul>
                                        </li>
                                    </ul>
                                </li>
                                <li>
                                    <Link to={"#"} className="has-arrow" >
                                        {SVGICON.Charts}
                                        <span className="nav-text">Charts</span>
                                        {/* <span className="badge badge-xs badge-light">06</span> */}
                                    </Link>
                                    <ul>
                                        <li><Link to={"/chart-rechart"}>RechartJs</Link></li>
                                        <li><Link to={"/chart-chartjs"}>Chartjs</Link></li>
                                        <li><Link to={"/chart-sparkline"}>Sparkline</Link></li>
                                        <li><Link to={"/chart-apexchart"}>Apexchart</Link></li>
                                    </ul>
                                </li>
                            </ul>
                        </Tab.Pane>
                        <Tab.Pane eventKey={"Bootstrap"}>
                            <ul className="metismenu tab-nav-menu">
                                <li className="nav-label">Components</li>
                                {componentArray.map((data, ind)=>(
                                    <li key={ind} className={`${data.title === menustate.active ? "mm-active" : ""}`}>
                                        <Link to={"#"} className="has-arrow"
                                            onClick={() => {handleMenuActive(data.title)}}
                                        >
                                            {data.iconStyle}
                                            {" "}<span className="nav-text">{data.title}</span>
                                            <span className="badge badge-xs badge-light">{data.number}</span>
                                        </Link>
                                        <Collapse in={menustate.active === data.title ? true :false}>
                                            <ul>
                                                {data.content && data.content.map((item,index) => {
                                                    return(
                                                        <li key={index}>
                                                            <a href="ui-accordion.html">{item.title}</a>
                                                        </li>
                                                    )
                                                })}
                                            </ul>
                                        </Collapse>
                                    </li>
                                ))}                               
                            </ul>
                        </Tab.Pane>
                        <Tab.Pane eventKey={"Form"}>
                            <ul className="metismenu tab-nav-menu">
                                <li className="nav-label">Forms</li>
                                <li className={`${state.collpase2 ? "mm-active" : ""}`}>
                                    <Link to={"#"} className="has-arrow ai-icon" 
                                        onClick={() => dispatch({type:'collpase2'})}
                                    >
                                        {SVGICON.Forms}
                                        <span className="nav-text">{" "}Forms</span>
                                        <span className="badge badge-xs badge-light">05</span>
                                    </Link>
                                    <Collapse in={state.collpase2}>
                                        <ul>
                                            <li><Link to={"/form-element"}>Form Elements</Link></li>
                                            <li><Link to={"/form-wizard"}>Wizard</Link></li>
                                            <li><Link to={"/form-ckeditor"}>CkEditor</Link></li>
                                            <li><Link to={"/form-pickers"}>Pickers</Link></li>
                                            <li><Link to={"/form-validation"}>Form Validate</Link></li>
                                        </ul>
                                    </Collapse>
                                </li>
                            </ul>
                        </Tab.Pane>
                        <Tab.Pane eventKey={"Table"}>
                            <ul className="metismenu tab-nav-menu">
                                <li className="nav-label">Table</li>
                                <li>
                                    <Link to={"table-bootstrap-basic"}>
                                       {SVGICON.Bootstrap} 
                                       {" "} Bootstrap
                                    </Link>
                                </li>
                                <li>
                                    <Link to={"/table-datatable-basic"}>
                                        {SVGICON.DataTable}
                                        {" "}Datatable
                                    </Link>
                                </li>
                            </ul>
                        </Tab.Pane>
                        <Tab.Pane eventKey={"Page"}>
                            <ul className="metismenu tab-nav-menu">
                                <li className="nav-label">Extra</li>                                                                
                                <li className={`${state.collpase3 ? "mm-active" : ""}`}>
                                    <Link to={"#"} className="has-arrow ai-icon" 
                                        onClick={() => dispatch({type:'collpase3'})}
                                    >
                                        {SVGICON.ErrorSvg}
                                        Error
                                        <span className="badge badge-xs badge-light">05</span>
                                    </Link>
                                    <Collapse in={state.collpase3}>
                                        <ul>
                                            <li><Link to={"/page-error-400"}>Error 400</Link></li>
                                            <li><Link to={"/page-error-403"}>Error 403</Link></li>
                                            <li><Link to={"/page-error-404"}>Error 404</Link></li>
                                            <li><Link to={"/page-error-500"}>Error 500</Link></li>
                                            <li><Link to={"/page-error-503"}>Error 503</Link></li>
                                        </ul>
                                    </Collapse>
                                </li>
                                <li>
                                    <Link to={"/page-lock-screen"}>
                                        {SVGICON.LockScreen}
                                        {" "}Lock Screen
                                    </Link>
                                </li>
                            </ul>
                        </Tab.Pane>
                        
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
                    <Nav as="ul" className="nav menu-tabs">
                        {sidebarMenu.map((item, index)=>(
                            <Nav.Item as="li" key={index}>
                                <Nav.Link className="ai-icon" eventKey={item.menuKey}
                                    onClick={()=>{
                                        setActiveMenu(index)                                    
                                        console.log(index);
                                    }}
                                >
                                    {item.mainicon}
                                </Nav.Link>
                            </Nav.Item>
                        ))}
                    </Nav>
                </div>
                <Link to={"#"} className="logout-btn">
                    {SVGICON.LogoutIocn}
                </Link>
            </div>
        </Tab.Container>
    </Fragment>
  );
};

export default Deflayout;

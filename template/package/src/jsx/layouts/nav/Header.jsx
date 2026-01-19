import React,{useContext, useState} from "react";

import { Link } from "react-router-dom";
/// Scroll

import { Dropdown } from "react-bootstrap";

/// Image
import profile from "../../../images/profile/pic1.jpg";
import avatar from "../../../images/avatar/1.jpg";

import LogoutPage from './Logout';
import { ThemeContext } from "../../../context/ThemeContext";
import { SVGICON } from "../../constant/theme";

const Header = ({ onNote }) => {	
  const { background, changeBackground } = useContext(ThemeContext);
  function ThemeChange(){    
    if(background.value === "light"){
      changeBackground({ value: "dark" });
    }else{
      changeBackground({value:"light"})
    }
  }
  const [fullScreen, setFullScreen] = useState(false);
	const onFullScreen = () => {
		var elem = document.documentElement;
		setFullScreen(elem ? true : false);

		if (elem.requestFullscreen) {
		  elem.requestFullscreen();
		} else if (elem.webkitRequestFullscreen) {
		  elem.webkitRequestFullscreen();
		} else if (elem.msRequestFullscreen) {
		  elem.msRequestFullscreen();
		}
	};
	const offFullScreen = () => {
		if (document.exitFullscreen) {
		  document.exitFullscreen();
		} else if (document.webkitExitFullscreen) {
		  /* Safari */
		  document.webkitExitFullscreen();
		} else if (document.msExitFullscreen) {
		  /* IE11 */
		  document.msExitFullscreen();
		}
		setFullScreen(false);
	};
  return (
    <div className="header">
      <div className="header-content">
        <nav className="navbar navbar-expand">
          <div className="collapse navbar-collapse justify-content-between">
            <div className="header-left">				
                <div className="search_bar dropdown">
                    <span className="search_icon p-3 c-pointer" data-bs-toggle="dropdown">
                        <i className="mdi mdi-magnify"></i>
                    </span>
                    <div className="dropdown-menu p-0 m-0">
                        <form>
                            <input className="form-control" type="search" placeholder="Search" aria-label="Search" />
                        </form>
                    </div>
                </div>
            </div>
            <ul className="navbar-nav header-right">
                <li className="nav-item dropdown notification_dropdown">
								  <Link to={"https://motaadmin.dexignlab.com/react"} className="nav-link" target="_blank">
                    {SVGICON.Trolly}
                    <div className="pluse-css-1"></div>
                  </Link>
                </li>
              <li className="nav-item dropdown notification_dropdown">
                <Link to={"#"} className={`nav-link bell dz-theme-mode ${ background.value === "dark" ? "active" : ""}`}
                  onClick={() => ThemeChange()}
                >
                    <i id="icon-light" className="fas fa-sun" />
                    <i id="icon-dark" className="fas fa-moon" />  
                </Link>
							</li>
              
              {fullScreen ? (
								<li
								  className="nav-item dropdown notification_dropdown"
								  onClick={() => offFullScreen()}
								>
								  <Link className="nav-link dz-fullscreen active" to="#">
                    <svg
                      id="icon-full"
                      viewBox="0 0 24 24"
                      width={20}
                      height={20}
                      stroke="currentColor"
                      strokeWidth={2}
                      fill="none"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      className="css-i6dzq1"
                    >
                      <path d="M8 3H5a2 2 0 0 0-2 2v3m18 0V5a2 2 0 0 0-2-2h-3m0 18h3a2 2 0 0 0 2-2v-3M3 16v3a2 2 0 0 0 2 2h3" />
                    </svg>
									
                    <svg
                      id="icon-minimize"
                      width={20}
                      height={20}
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth={2}
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      className="feather feather-minimize"
                    >
                      <path d="M8 3v3a2 2 0 0 1-2 2H3m18 0h-3a2 2 0 0 1-2-2V3m0 18v-3a2 2 0 0 1 2-2h3M3 16h3a2 2 0 0 1 2 2v3" />
                    </svg>
								  </Link>
								</li>
							  ) : (
								<li className="nav-item dropdown notification_dropdown">
								  <Link
                    className="nav-link dz-fullscreen"
                    to="#"
                    onClick={() => onFullScreen()}
								  >
                    <svg
                        id="icon-full"
                        viewBox="0 0 24 24"
                        width={20}
                        height={20}
                        stroke="currentColor"
                        strokeWidth={2}
                        fill="none"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        className="css-i6dzq1"
                    >
									  <path d="M8 3H5a2 2 0 0 0-2 2v3m18 0V5a2 2 0 0 0-2-2h-3m0 18h3a2 2 0 0 0 2-2v-3M3 16v3a2 2 0 0 0 2 2h3" />
									  </svg>
                    <svg
                      id="icon-minimize"
                      width={20}
                      height={20}
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth={2}
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      className="feather feather-minimize"
                    >
                      <path d="M8 3v3a2 2 0 0 1-2 2H3m18 0h-3a2 2 0 0 1-2-2V3m0 18v-3a2 2 0 0 1 2-2h3M3 16h3a2 2 0 0 1 2 2v3" />
                    </svg>
								  </Link>
								</li>
							)}
			       <Dropdown as="li" className="nav-item  notification_dropdown ">
                <Dropdown.Toggle variant="" as="a"
                  className="nav-link bell ai-icon i-false c-pointer icon-bell-effect"                 
                  role="button"
                  data-toggle="dropdown"
                >
                  <svg id="icon-user" xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="feather feather-bell">
                      <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"></path>
                      <path d="M13.73 21a2 2 0 0 1-3.46 0"></path>
                  </svg>
                  <div className="pulse-css"></div>
                </Dropdown.Toggle>
                <Dropdown.Menu align="end" className="">
                  <div className="widget-media dz-scroll p-3 height380" style={{height: "380px"}}>
                    <ul className="timeline">
                      <li>
                        <div className="timeline-panel">
                          <div className="media me-2">
                            <img alt="images" width={50} src={avatar} />
                          </div>
                          <div className="media-body">
                            <h6 className="mb-1">Dr sultads Send you Photo</h6>
                            <small className="d-block">
                              29 July 2020 - 02:26 PM
                            </small>
                          </div>
                        </div>
                      </li>
                      <li>
                        <div className="timeline-panel">
                          <div className="media me-2 media-info">KG</div>
                          <div className="media-body">
                            <h6 className="mb-1">
                              Resport created successfully
                            </h6>
                            <small className="d-block">
                              29 July 2020 - 02:26 PM
                            </small>
                          </div>
                        </div>
                      </li>
                      <li>
                        <div className="timeline-panel">
                          <div className="media me-2 media-success">
                            <i className="fa fa-home" />
                          </div>
                          <div className="media-body">
                            <h6 className="mb-1">Reminder : Treatment Time!</h6>
                            <small className="d-block">
                              29 July 2020 - 02:26 PM
                            </small>
                          </div>
                        </div>
                      </li>
                      <li>
                        <div className="timeline-panel">
                          <div className="media me-2">
                            <img alt="" width={50} src={avatar} />
                          </div>
                          <div className="media-body">
                            <h6 className="mb-1">Dr sultads Send you Photo</h6>
                            <small className="d-block">
                              29 July 2020 - 02:26 PM
                            </small>
                          </div>
                        </div>
                      </li>
                      <li>
                        <div className="timeline-panel">
                          <div className="media me-2 media-danger">KG</div>
                          <div className="media-body">
                            <h6 className="mb-1">
                              Resport created successfully
                            </h6>
                            <small className="d-block">
                              29 July 2020 - 02:26 PM
                            </small>
                          </div>
                        </div>
                      </li>
                      <li>
                        <div className="timeline-panel">
                          <div className="media me-2 media-primary">
                            <i className="fa fa-home" />
                          </div>
                          <div className="media-body">
                            <h6 className="mb-1">Reminder : Treatment Time!</h6>
                            <small className="d-block">
                              29 July 2020 - 02:26 PM
                            </small>
                          </div>
                        </div>
                      </li>
                    </ul>
                    {/* <div className="ps__rail-x" style={{ left: 0, bottom: 0 }}>
                      <div
                        className="ps__thumb-x"
                        tabIndex={0}
                        style={{ left: 0, width: 0 }}
                      />
                    </div>
                    <div className="ps__rail-y" style={{ top: 0, right: 0 }}>
                      <div
                        className="ps__thumb-y"
                        tabIndex={0}
                        style={{ top: 0, height: 0 }}
                      />
                    </div> */}
                  </div>
                  <Link className="all-notification" to="#">
                    See all notifications <i className="ti-arrow-right" />
                  </Link>
                </Dropdown.Menu>
              </Dropdown>				
			        <Dropdown as="li" className="nav-item dropdown header-profile">
                <Dropdown.Toggle variant="" as="a" className="nav-link i-false c-pointer">
                    <img src={profile} width={20} alt="" />
                    <div className="header-info">
                      <span>Hey, <strong>Joshua</strong></span>
										  <small>Business Profile</small>
                    </div>
                </Dropdown.Toggle>
                <Dropdown.Menu align="end" className="mt-0 dropdown-menu-end">
                  <Link to="/app-profile" className="dropdown-item ai-icon">
                    <svg
                      id="icon-user1" xmlns="http://www.w3.org/2000/svg" className="text-primary"
                      width={18} height={18} viewBox="0 0 24 24" fill="none"
                      stroke="currentColor" strokeWidth={2} strokeLinecap="round"strokeLinejoin="round"
                    >
                      <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
                      <circle cx={12} cy={7} r={4} />
                    </svg>
                    <span className="ms-2">Profile </span>
                  </Link>
                  <Link to="/email-inbox" className="dropdown-item ai-icon">
                    <svg id="icon-inbox" xmlns="http://www.w3.org/2000/svg" className="text-success"
                      width={18} height={18} viewBox="0 0 24 24" fill="none" stroke="currentColor"
                      strokeWidth={2} strokeLinecap="round" strokeLinejoin="round"
                    >
                      <path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z" />
                      <polyline points="22,6 12,13 2,6" />
                    </svg>
                    <span className="ms-2">Inbox </span>
                  </Link>
                  <LogoutPage />
                </Dropdown.Menu>
              </Dropdown>
              <Dropdown as="li" className="nav-item right-sidebar">
                <Dropdown.Toggle
                  variant=""
                  as="a"
                  className="nav-link bell i-false c-pointer ai-icon"
                  onClick={() => onNote()}
                >
                  <svg id="icon-menu" viewBox="0 0 24 24" width="24" height="24" stroke="currentColor" strokeWidth="2" fill="none" 
                    strokeLinecap="round" strokeLinejoin="round" className="css-i6dzq1 hoverEffect"                   
                  >
                      <rect x="3" y="3" width="7" height="7" style={{strokeDasharray: "28px 48px"}}></rect>
                      <rect x="14" y="3" width="7" height="7" style={{strokeDasharray: "28px 48px"}}></rect>
                      <rect x="14" y="14" width="7" height="7" style={{strokeDasharray: "28px 48px"}}></rect>
                      <rect x="3" y="14" width="7" height="7" style={{strokeDasharray: "28px 48px"}}></rect>
                    </svg>                  
                </Dropdown.Toggle>
              </Dropdown>
            </ul>
          </div>
        </nav>
      </div>
    </div>
  );
};

export default Header;

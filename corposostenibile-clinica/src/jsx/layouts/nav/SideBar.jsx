import React, { useContext, useEffect, useReducer, useState } from "react";
import { Collapse } from 'react-bootstrap';
/// Link
import { Link } from "react-router-dom";
import { MenuList } from './Menu';
import { ThemeContext } from "../../../context/ThemeContext";
import { useAuth } from "../../../context/AuthContext";

const reducer = (previousState, updatedState) => ({
  ...previousState,
  ...updatedState,
});

const initialState = {
  active: "",
  activeSubmenu: "",
}

const SideBar = () => {
  const {
    iconHover,
    sidebarposition,
    headerposition,
    sidebarLayout,
    ChangeIconSidebar,
  } = useContext(ThemeContext);

  const { user } = useAuth();

  const [state, setState] = useReducer(reducer, initialState);
  const handleMenuActive = status => {
    setState({ active: status });
    if (state.active === status) {
      setState({ active: "" });
    }
  }
  const handleSubmenuActive = (status) => {
    setState({ activeSubmenu: status })
    if (state.activeSubmenu === status) {
      setState({ activeSubmenu: "" })
    }
  }

  //For scroll
  const [hideOnScroll, setHideOnScroll] = useState(true)

  // ForAction Menu
  let path = window.location.pathname;
  path = path.split("/");
  path = path[path.length - 1];

  useEffect(() => {
    MenuList.forEach((data) => {
      data.content?.forEach((item) => {
        if (path === item.to) {
          setState({ active: data.title })
        }
        item.content?.forEach(ele => {
          if (path === ele.to) {
            setState({ activeSubmenu: item.title, active: data.title })
          }
        })
      })
    })
  }, [path]);
  return (
    <div
      onMouseEnter={() => ChangeIconSidebar(true)}
      onMouseLeave={() => ChangeIconSidebar(false)}
      className={`deznav ${iconHover} ${sidebarposition.value === "fixed" &&
        sidebarLayout.value === "horizontal" &&
        headerposition.value === "static"
        ? hideOnScroll > 120
          ? "fixed"
          : ""
        : ""
        }`}
    >

      <div className="deznav-scroll">
        <ul className="metismenu" id="menu">
          {(user?.role === 'influencer' 
            ? MenuList.filter(item => ['Pazienti', 'Profilo', 'CLIENTI', 'TEAM'].includes(item.title))
            : MenuList.filter(item => {
                // Nascondi Quality per utenti non admin
                if (item.title === 'Quality' && !(user?.is_admin || user?.role === 'admin')) {
                  return false;
                }
                return true;
              })
          ).map((data, index) => {
            let menuClass = data.classsChange;
            if (menuClass === "menu-title") {
              return (
                <li className={`nav-label  ${menuClass} ${data.extraclass}`} key={index}>{data.title}</li>
              )
            } else {
              return (
                <li className={`has-menu ${state.active === data.title ? 'mm-active' : ''}${data.to === path ? 'mm-active' : ''} `}
                  key={index}
                >
                  {data.content && data.content.length > 0 ?
                    <>
                      <Link to={"#"}
                        className="has-arrow ai-icon"
                        onClick={() => { handleMenuActive(data.title) }}
                      >
                        {data.iconStyle}{" "}
                        <span className="nav-text">{data.title}
                          <span className="badge badge-xs style-1 badge-danger ms-2">{data.update}</span>
                        </span>
                      </Link>

                      <Collapse in={state.active === data.title ? true : false}>
                        <ul className={`${menuClass === "mm-collapse" ? "mm-show" : ""}`}>
                          {data.content && data.content.map((data, index) => {
                            return (
                              <li key={index}
                                className={`${state.activeSubmenu === data.title ? "mm-active" : ""}${data.to === path ? 'mm-active' : ''}`}
                              >
                                {data.content && data.content.length > 0 ?
                                  <>
                                    <Link to={data.to} className={data.hasMenu ? 'has-arrow' : ''}
                                      onClick={() => { handleSubmenuActive(data.title) }}
                                    >
                                      {data.title}
                                    </Link>
                                    <Collapse in={state.activeSubmenu === data.title ? true : false}>
                                      <ul className={`${menuClass === "mm-collapse" ? "mm-show" : ""}`}>
                                        {data.content && data.content.map((data, index) => {
                                          return (
                                            <li key={index}>
                                              <Link className={`${path === data.to ? "mm-active" : ""}`} to={data.to}>{data.title}</Link>
                                            </li>
                                          )
                                        })}
                                      </ul>
                                    </Collapse>
                                  </>
                                  :
                                  <Link to={data.to}
                                    className={`${data.to === path ? 'mm-active' : ''}`}
                                  >
                                    {data.title}
                                  </Link>
                                }

                              </li>

                            )
                          })}
                        </ul>
                      </Collapse>
                    </>
                    :
                    <Link
                      to={data.isProfile && user ? `team-dettaglio/${user.id}` : data.to}
                      className={`${data.to === path ? 'mm-active' : ''}`}
                    >
                      {data.iconStyle}{" "}
                      <span className="nav-text">
                        {data.isProfile && user ? user.full_name || user.first_name : data.title}
                        <span className="badge badge-xs style-1 badge-danger ms-2">{data.update}</span>
                      </span>
                    </Link>
                  }
                </li>
              )
            }
          })}

          {/* Admin Settings - solo per admin */}
          {(user?.is_admin || user?.role === 'admin') && (
            <>
              <li className="nav-label menu-title">Impostazioni</li>
              <li className={path === 'admin/ghl-settings' ? 'mm-active' : ''}>
                <Link to="/admin/ghl-settings" className={path === 'admin/ghl-settings' ? 'mm-active' : ''}>
                  <i className="ri-settings-3-line" style={{ fontSize: '20px', marginRight: '10px' }}></i>
                  <span className="nav-text">GHL Settings</span>
                </Link>
              </li>
              <li className={path === 'admin/origins' ? 'mm-active' : ''}>
                <Link to="/admin/origins" className={path === 'admin/origins' ? 'mm-active' : ''}>
                  <i className="ri-global-line" style={{ fontSize: '20px', marginRight: '10px' }}></i>
                  <span className="nav-text">Gestione Origini</span>
                </Link>
              </li>
            </>
          )}
        </ul>


      </div>

    </div>
  );

}

export default SideBar;

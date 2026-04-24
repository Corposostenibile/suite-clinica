import React, { useContext, useEffect, useReducer, useState } from "react";
import { Collapse } from 'react-bootstrap';
/// Link
import { Link } from "react-router-dom";
import { MenuList } from './Menu';
import { ThemeContext } from "../../../context/ThemeContext";
import { useAuth } from "../../../context/AuthContext";
import {
  canAccessAiAssignments,
  canAccessCapacity,
  canAccessGlobalCheckPage,
  canAccessLoomLibrary,
  canAccessQualityPage,
  canAccessTeamLists,
  canAccessTrialPages,
  isHealthManagerTeamLeader,
  isHealthManagerUser,
  isMarketingUser,
  isProfessionistaStandard,
} from "../../../utils/rbacScope";

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
          {(isMarketingUser(user)
            ? MenuList.filter(item => ['Dashboard', 'Visuale Marketing', 'MAIN MENU', 'CLIENTI'].includes(item.title))
            : isHealthManagerTeamLeader(user)
            ? MenuList.filter(item => ['Pazienti', 'Assegnazioni v1', 'Assegnazioni v2', 'Libreria Loom', 'Team', 'Professionisti', 'Capienze', 'Calendario', 'Check', 'Formazione', 'CLIENTI', 'TEAM', 'MAIN MENU'].includes(item.title))
            : isHealthManagerUser(user)
            ? MenuList.filter(item => ['Pazienti', 'Assegnazioni v1', 'Assegnazioni v2', 'Libreria Loom', 'Calendario', 'Check', 'CLIENTI', 'TEAM', 'MAIN MENU'].includes(item.title))
            : user?.role === 'influencer'
            ? MenuList.filter(item => ['Dashboard', 'Pazienti', 'Check', 'MAIN MENU', 'CLIENTI'].includes(item.title))
            : user?.is_trial
              ? MenuList.filter(item => {
                // Trial users - filtra per stage
                if (user.trial_stage === 1) {
                  // Stage 1: Solo Dashboard e Formazione
                  return ['Dashboard', 'Formazione', 'MAIN MENU'].includes(item.title);
                } else if (user.trial_stage === 2) {
                  // Stage 2: Dashboard, Formazione + Pazienti
                  return ['Dashboard', 'Formazione', 'Pazienti', 'MAIN MENU', 'CLIENTI'].includes(item.title);
                } else {
                  // Stage 3+ (già promosso): menu completo
                  if (item.title === 'Quality' && !(user?.is_admin || user?.role === 'admin' || user?.role === 'team_leader')) {
                    return false;
                  }
                  return true;
                }
              })
              : MenuList.filter(item => {
                if (item.title === 'Quality' && !canAccessQualityPage(user)) {
                  return false;
                }
                if (item.title === 'Assegnazioni v2' && !canAccessAiAssignments(user)) {
                  return false;
                }
                if (item.title === 'Assegnazioni v1' && !canAccessAiAssignments(user)) {
                  return false;
                }
                if (item.title === 'Capienze' && !canAccessCapacity(user)) return false;
                if (item.title === 'Check' && !canAccessGlobalCheckPage(user)) return false;
                if (item.title === 'In Prova' && !canAccessTrialPages(user)) return false;
                if (item.title === 'Libreria Loom' && !canAccessLoomLibrary(user)) return false;
                // "Visuale Marketing" non compare nella sidebar per admin/CCO:
                // e accessibile solo come pill dentro le viste lista pazienti.
                // Il ruolo marketing la vede tramite il branch isMarketingUser sopra.
                if (item.title === 'Visuale Marketing') return false;
                if ((item.title === 'Team' || item.title === 'Professionisti') && !canAccessTeamLists(user)) {
                  return false;
                }
                return true;
              })
          ).map((data, index) => {
            let menuClass = data.classsChange;
            if (menuClass === "menu-title") {
              if (menuClass !== "menu-title" && user && isProfessionistaStandard(user) && data.title === 'TEAM') {
                return null;
              }
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
                        {data.isProfile && user ? user.first_name || data.title : data.title}
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
              <li className={path === 'admin/capacity-weights' ? 'mm-active' : ''}>
                <Link to="/admin/capacity-weights" className={path === 'admin/capacity-weights' ? 'mm-active' : ''}>
                  <i className="ri-scales-3-line" style={{ fontSize: '20px', marginRight: '10px' }}></i>
                  <span className="nav-text">Pesi Capienza</span>
                </Link>
              </li>
              {!user?.impersonating && (
                <li className={path === 'admin/impersonate' ? 'mm-active' : ''}>
                  <Link to="/admin/impersonate" className={path === 'admin/impersonate' ? 'mm-active' : ''}>
                    <i className="ri-user-shared-line" style={{ fontSize: '20px', marginRight: '10px' }}></i>
                    <span className="nav-text">Accedi come</span>
                  </Link>
                </li>
              )}
            </>
          )}
        </ul>


      </div>

    </div>
  );

}

export default SideBar;

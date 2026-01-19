import React, {  useContext } from "react";
import { useDispatch , useSelector } from 'react-redux';
import { Link } from "react-router-dom";

import { navtoggle } from "../../../store/actions/AuthActions";
import { ThemeContext } from "../../../context/ThemeContext";

/// images
import logo from "../../../images/logo-white.png";
import logoText from "../../../images/logo-text-white.png";

const NavHeader2 = ({openSidebar}) => {  
  const {  openMenuToggle } = useContext(
    ThemeContext
  );
    
    const dispatch = useDispatch();
    const sideMenu = useSelector(state => state.sideMenu);
    const handleToogle = () => {
      dispatch(navtoggle());
    };
  return (
    <div className="nav-header">
      <Link to="/dashboard" className="brand-logo">
          <img className="logo-abbr" src={logo} alt="" />
          <img className="logo-compact" src={logoText} alt="" />
          <img className="brand-title" src={logoText} alt="" />
      </Link>

      <div
        className="nav-control"
        onClick={() => {
          handleToogle()
          openMenuToggle();
        }}
      >
        <div className={`hamburger ${sideMenu ? "is-active" : ""} ${openSidebar ? 'd-none': ''}`}
        >
          <span className="line"></span>
          <span className="line"></span>
          <span className="line"></span>
        </div>
      </div>
    </div>
  );
};

export default NavHeader2;

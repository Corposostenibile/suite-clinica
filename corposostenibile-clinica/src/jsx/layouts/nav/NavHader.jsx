import React, { useContext, useState } from "react";
import { Link } from "react-router-dom";

import { ThemeContext } from "../../../context/ThemeContext";

/// images
import logo from "../../../images/logo-foglia-white.png";

const logoTextStyle = {
  color: '#fff',
  fontSize: '20px',
  fontWeight: 700,
  letterSpacing: '3px',
  textTransform: 'uppercase',
  fontFamily: "'Poppins', sans-serif",
  marginLeft: '10px',
};

const NavHader = () => {
  const { openMenuToggle } = useContext(ThemeContext);

  const [toggle, setToggle] = useState(false);

  const handleToogle = () => {
    setToggle(!toggle);
  };

  return (
    <div className="nav-header">
      <Link to="/dashboard" className="brand-logo">
        <img className="logo-abbr" src={logo} alt="" />
        <span className="logo-compact" style={logoTextStyle}>CLINICA</span>
        <span className="brand-title" style={logoTextStyle}>CLINICA</span>
      </Link>

      <div
        className="nav-control"
        onClick={() => {
          handleToogle();
          openMenuToggle();
        }}
      >
        <div className={`hamburger ${toggle ? "is-active" : ""}`}>
          <span className="line"></span>
          <span className="line"></span>
          <span className="line"></span>
        </div>
      </div>
    </div>
  );
};

export default NavHader;

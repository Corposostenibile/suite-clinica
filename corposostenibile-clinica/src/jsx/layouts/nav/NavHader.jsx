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
  const [animating, setAnimating] = useState(false);

  const handleToogle = () => {
    setAnimating(true);
    setToggle(!toggle);
    setTimeout(() => setAnimating(false), 450);
  };

  return (
    <div className="nav-header">
      <Link to="/welcome" className="brand-logo">
        <img className="logo-abbr" src={logo} alt="" />
        <span className="logo-compact" style={logoTextStyle}>CLINICA</span>
        <span className="brand-title" style={logoTextStyle}>CLINICA</span>
      </Link>

      <div
        className={`nav-control${animating ? ' nav-control--pop' : ''}`}
        onClick={() => {
          handleToogle();
          openMenuToggle();
        }}
      >
        {toggle ? (
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#25B36A" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
            <polyline points="9 18 15 12 9 6" />
          </svg>
        ) : (
          <div className="hamburger">
            <span className="line"></span>
            <span className="line"></span>
            <span className="line"></span>
          </div>
        )}
      </div>
    </div>
  );
};

export default NavHader;

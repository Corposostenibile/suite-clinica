import React, { useContext } from "react";
import { Link } from "react-router-dom";

import { ThemeContext } from "../../../context/ThemeContext";

/// images
import logo from "../../../images/logo-foglia-white.png";

const NAV_COMPACT_SIZE = 44;

const logoTextStyle = {
  color: '#fff',
  fontSize: '20px',
  fontWeight: 700,
  letterSpacing: '3px',
  textTransform: 'uppercase',
  fontFamily: "'Poppins', sans-serif",
  marginLeft: '10px',
};

const NavHader = ({ compactTopBar }) => {
  const { openMenuToggle, menuToggle } = useContext(ThemeContext);

  if (compactTopBar) {
    return (
      <div
        className="nav-header compact-nav-header"
        style={{
          height: NAV_COMPACT_SIZE,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '0 10px',
          boxSizing: 'border-box',
          zIndex: 1000,
        }}
      >
        <Link to="/dashboard" className="brand-logo compact-brand-logo">
          <img className="logo-abbr" src={logo} alt="" style={{ width: '40px' }} />
          <span className="logo-compact" style={logoTextStyle}>CLINICA</span>
          <span className="brand-title" style={logoTextStyle}>CLINICA</span>
        </Link>
        <div
          className="nav-control"
          role="button"
          tabIndex={0}
          onClick={() => openMenuToggle()}
          onKeyDown={(e) => e.key === 'Enter' && openMenuToggle()}
          style={{ position: 'relative', transform: 'none' }}
        >
          <div className={`hamburger ${menuToggle ? "is-active" : ""}`}>
            <span className="line" style={{ background: '#fff' }}></span>
            <span className="line" style={{ background: '#fff' }}></span>
            <span className="line" style={{ background: '#fff' }}></span>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="nav-header">
      <Link to="/dashboard" className="brand-logo">
        <img className="logo-abbr" src={logo} alt="" />
        <span className="logo-compact" style={logoTextStyle}>CLINICA</span>
        <span className="brand-title" style={logoTextStyle}>CLINICA</span>
      </Link>

      <div
        className="nav-control"
        onClick={() => openMenuToggle()}
      >
        <div className={`hamburger ${menuToggle ? "is-active" : ""}`}>
          <span className="line" style={{ background: '#fff' }}></span>
          <span className="line" style={{ background: '#fff' }}></span>
          <span className="line" style={{ background: '#fff' }}></span>
        </div>
      </div>
    </div>
  );
};

export default NavHader;

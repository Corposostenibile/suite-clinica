import { Link } from 'react-router-dom';
import logoAbbr from '../images/logo_foglia.png';
import logoText from '../images/Suite.png';

function NavHeader({ sidebarCollapsed, onToggle }) {
  return (
    <div className="nav-header">
      <Link to="/welcome" className="brand-logo">
        <img className="logo-abbr" src={logoAbbr} alt="logo" />
        <img className="brand-title" src={logoText} alt="Corposostenibile Suite" />
      </Link>

      <div className="nav-control" onClick={onToggle}>
        <div className={`hamburger ${sidebarCollapsed ? '' : 'is-active'}`}>
          <span className="line"></span>
          <span className="line"></span>
          <span className="line"></span>
        </div>
      </div>
    </div>
  );
}

export default NavHeader;

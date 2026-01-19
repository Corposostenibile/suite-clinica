import React  from 'react';
import {connect, useDispatch } from 'react-redux';
import { useLocation, useNavigate, useParams } from 'react-router-dom';

import { Logout } from '../../../store/actions/AuthActions';
import { isAuthenticated } from '../../../store/selectors/AuthSelectors';
import { SVGICON } from '../../constant/theme';

function withRouter(Component) {
    function ComponentWithRouterProp(props) {
      let location = useLocation();
      let navigate = useNavigate();
      let params = useParams();
      return (
        <Component
          {...props}
          router={{ location, navigate, params }}
        />
      );
    }
  
    return ComponentWithRouterProp;
}

function LogoutMini(){
    const dispatch = useDispatch();
    const navigate = useNavigate();
    function onLogout() {
       dispatch(Logout(navigate));
    }
    return(
        <>
            <button  className="logout-btn mini-btn" onClick={onLogout}>
                {SVGICON.LogoutIocn}
            </button>
        </>
    )
} 
const mapStateToProps = (state) => {
    return {
        isAuthenticated: isAuthenticated(state),
    };
};

export default withRouter(connect(mapStateToProps)(LogoutMini));
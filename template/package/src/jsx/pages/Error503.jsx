import React from "react";
import { Link } from "react-router-dom";

import Error from '../../images/error.svg';

const Error503 = () => {
   return (
      <div className="fix-wrapper bg-white">
         <div className="container">
            <div className="row  align-items-center">
               <div className="col-lg-6 col-sm-6">
                  <div className="form-input-content  error-page">
                     <h1 className="error-text text-primary">503</h1>
                     <h4>Service Unavailable</h4>
                     <p>Sorry, we are under maintenance! </p>
                     <Link to={"/dashboard"} className="btn btn-primary">Back to Home</Link>
                  </div>
               </div>
               <div className="col-lg-6 col-sm-6">
                  <img className="w-100" src={Error} alt="" />
               </div>
            </div>
         </div>
      </div>
   );
};

export default Error503;

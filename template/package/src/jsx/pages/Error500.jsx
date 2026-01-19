import React from "react";
import { Link } from "react-router-dom";


import Error from '../../images/error.svg';

const Error500 = () => {
   return (
      <div className="fix-wrapper bg-white">
         <div className="container">
            <div className="row  align-items-center">
               <div className="col-lg-6 col-sm-6">
                  <div className="form-input-content  error-page">
                     <h1 className="error-text text-primary">500</h1>
                     <h4>Internal Server Error</h4>
                     <p>You do not have permission to view this resource</p>
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

export default Error500;

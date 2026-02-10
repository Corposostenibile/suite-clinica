import React from 'react';
import { Navigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

const RoleProtectedRoute = ({ children, allowedRoles, deniedRoles }) => {
    const { user, loading } = useAuth();

    if (loading) {
        return (
            <div id="preloader">
                <div className="sk-three-bounce">
                    <div className="sk-child sk-bounce1"></div>
                    <div className="sk-child sk-bounce2"></div>
                    <div className="sk-child sk-bounce3"></div>
                </div>
            </div>
        );
    }

    if (!user) {
        return <Navigate to="/auth/login" replace />;
    }

    const userRole = user.role;
    const isAdmin = user.is_admin === true || userRole === 'admin';

    // Gli admin possono sempre accedere a tutto (opzionale, ma comune)
    if (isAdmin) {
        return children;
    }

    if (allowedRoles && !allowedRoles.includes(userRole)) {
        return <Navigate to="/welcome" replace />;
    }

    if (deniedRoles && deniedRoles.includes(userRole)) {
        return <Navigate to="/welcome" replace />;
    }

    return children;
};

export default RoleProtectedRoute;

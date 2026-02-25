/**
 * SmartV2X-CP Ultra — App Shell
 * Root component with auth-gated routing.
 */
import React from 'react';
import { AuthProvider, useAuth } from './context/AuthContext';
import Login from './components/Login';
import Dashboard from './pages/Dashboard';

function AppContent() {
    const { user } = useAuth();
    return user ? <Dashboard /> : <Login />;
}

export default function App() {
    return (
        <AuthProvider>
            <AppContent />
        </AuthProvider>
    );
}

/**
 * SmartV2X-CP Ultra — Auth Context
 * React context for authentication state management.
 */
import React, { createContext, useContext, useState, useEffect } from 'react';
import { getStoredToken, getStoredUser, storeAuth, clearAuth } from '../api/auth';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
    const [user, setUser] = useState(null);
    const [token, setToken] = useState(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const savedToken = getStoredToken();
        const savedUser = getStoredUser();
        if (savedToken && savedUser) {
            setToken(savedToken);
            setUser(savedUser);
        }
        setLoading(false);
    }, []);

    const handleLogin = (tokenData) => {
        // We expect { access_token: "...", token_type: "bearer" }
        // For the user object, we can decode the JWT or just store the username if we have it.
        // For simplicity in this demo, we'll store a generic user object.
        const userData = {
            username: "User", // This could be extracted from JWT payload if needed
            role: "admin",
        };
        storeAuth(tokenData.access_token, userData);
        setToken(tokenData.access_token);
        setUser(userData);
    };

    const handleLogout = () => {
        clearAuth();
        setToken(null);
        setUser(null);
    };

    if (loading) return null;

    return (
        <AuthContext.Provider value={{ user, token, login: handleLogin, logout: handleLogout }}>
            {children}
        </AuthContext.Provider>
    );
}

export function useAuth() {
    const ctx = useContext(AuthContext);
    if (!ctx) throw new Error('useAuth must be used within AuthProvider');
    return ctx;
}

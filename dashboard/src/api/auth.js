/**
 * SmartV2X-CP Ultra — Auth API Module
 * JWT authentication functions for login, register, and Google OAuth.
 */

const API_URL = import.meta.env.VITE_API_URL || '';

export async function login(username, password) {
    const response = await fetch(`${API_URL}/backend/api/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password }),
    });

    if (!response.ok) {
        const err = await response.json().catch(() => ({}));
        throw new Error(err.detail || 'Login failed');
    }

    return response.json();
}

export async function register(username, password, primary_vehicle_name = 'My Vehicle') {
    const response = await fetch(`${API_URL}/backend/api/auth/register`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password, primary_vehicle_name }),
    });

    if (!response.ok) {
        const err = await response.json().catch(() => ({}));
        throw new Error(err.detail || 'Registration failed');
    }

    return response.json();
}

export async function googleLogin(idToken) {
    const response = await fetch(`${API_URL}/backend/api/auth/google`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id_token: idToken }),
    });

    if (!response.ok) {
        const err = await response.json().catch(() => ({}));
        throw new Error(err.detail || 'Google login failed');
    }

    return response.json();
}

export function getStoredToken() {
    return localStorage.getItem('v2x_token');
}

export function getStoredUser() {
    const raw = localStorage.getItem('v2x_user');
    return raw ? JSON.parse(raw) : null;
}

export function storeAuth(token, user) {
    localStorage.setItem('v2x_token', token);
    localStorage.setItem('v2x_user', JSON.stringify(user));
}

export function clearAuth() {
    localStorage.removeItem('v2x_token');
    localStorage.removeItem('v2x_user');
}

export function authHeaders() {
    const token = getStoredToken();
    return token ? { Authorization: `Bearer ${token}` } : {};
}

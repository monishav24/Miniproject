/**
 * SmartV2X-CP Ultra — Premium Authentication
 * Split-screen layout with mobility-tech illustration and glassmorphism form.
 */
import React, { useState, useCallback } from 'react';
import { login as apiLogin, register as apiRegister, googleLogin as apiGoogleLogin } from '../api/auth';
import { useAuth } from '../context/AuthContext';
import GoogleSignInButton from './GoogleSignInButton';

/* ─── Neural Network SVG Illustration ─────────────────────── */
function MobilityIllustration() {
    return (
        <div className="auth-illustration">
            <svg viewBox="0 0 800 600" fill="none" xmlns="http://www.w3.org/2000/svg">
                <circle cx="400" cy="300" r="100" stroke="#22d3ee" strokeWidth="2" strokeDasharray="10 10" className="pulse-circle" />
                <path d="M200 150L350 250M600 150L450 250M200 450L350 350M600 450L450 350" stroke="#3b82f6" strokeWidth="2" opacity="0.5" />
                <rect x="350" y="250" width="100" height="100" rx="20" fill="#0f172a" stroke="#22d3ee" strokeWidth="2" />
                <path d="M375 290L425 310M375 310L425 290" stroke="#22d3ee" strokeWidth="2" strokeLinecap="round" />
                {/* Floating nodes */}
                <circle cx="200" cy="150" r="8" fill="#3b82f6" fillOpacity="0.8" />
                <circle cx="600" cy="150" r="8" fill="#22d3ee" fillOpacity="0.8" />
                <circle cx="200" cy="450" r="8" fill="#22d3ee" fillOpacity="0.8" />
                <circle cx="600" cy="450" r="8" fill="#3b82f6" fillOpacity="0.8" />
            </svg>
            <div style={{ textAlign: 'center', marginTop: '20px' }}>
                <h2 style={{ fontSize: '32px', fontWeight: '800', background: 'linear-gradient(to right, #22d3ee, #3b82f6)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
                    Next-Gen Mobility AI
                </h2>
                <p style={{ color: 'var(--text-secondary)', fontSize: '18px', maxWidth: '400px', margin: '10px auto' }}>
                    Zero-latency collision prediction and real-time V2X analytics for autonomous fleets.
                </p>
            </div>
        </div>
    );
}

export default function Login() {
    const { login } = useAuth();
    const [isLogin, setIsLogin] = useState(true);
    const [username, setUsername] = useState('');
    const [password, setPassword] = useState('');
    const [name, setName] = useState('');
    const [error, setError] = useState('');
    const [loading, setLoading] = useState(false);
    const [successMsg, setSuccessMsg] = useState('');

    const handleSubmit = async (e) => {
        e.preventDefault();
        setLoading(true);
        setError('');
        try {
            if (isLogin) {
                const data = await apiLogin(username, password);
                login(data);
            } else {
                const data = await apiRegister(username, password, name);
                setSuccessMsg('Account created! Entering platform...');
                setTimeout(() => login(data), 1000);
            }
        } catch (err) {
            setError(err.message || 'Authentication failed');
        } finally {
            setLoading(false);
        }
    };

    const handleGoogleSuccess = useCallback(async (idToken) => {
        setLoading(true);
        try {
            const data = await apiGoogleLogin(idToken);
            login(data);
        } catch (err) {
            setError(err.message || 'Google sign-in failed');
        } finally {
            setLoading(false);
        }
    }, [login]);

    return (
        <div className="auth-page">
            <div className="auth-sidebar">
                <MobilityIllustration />
            </div>

            <div className="auth-form-container">
                <div className="auth-card glass">
                    <div style={{ marginBottom: '32px' }}>
                        <h1 style={{ fontSize: '28px', fontWeight: '800', marginBottom: '8px' }}>
                            {isLogin ? 'Welcome Back' : 'Create Account'}
                        </h1>
                        <p style={{ color: 'var(--text-secondary)' }}>
                            {isLogin ? 'Enter your credentials to manage your fleet' : 'Join the V2X network today'}
                        </p>
                    </div>

                    <form onSubmit={handleSubmit}>
                        {!isLogin && (
                            <div style={{ marginBottom: '20px' }}>
                                <label style={{ fontSize: '14px', fontWeight: '600', color: 'var(--text-secondary)' }}>FULL NAME</label>
                                <input
                                    className="auth-input"
                                    type="text"
                                    placeholder="John Doe"
                                    value={name}
                                    onChange={(e) => setName(e.target.value)}
                                    required
                                />
                            </div>
                        )}

                        <div style={{ marginBottom: '20px' }}>
                            <label style={{ fontSize: '14px', fontWeight: '600', color: 'var(--text-secondary)' }}>USERNAME</label>
                            <input
                                className="auth-input"
                                type="text"
                                placeholder="v2x_user_01"
                                value={username}
                                onChange={(e) => setUsername(e.target.value)}
                                required
                            />
                        </div>

                        <div style={{ marginBottom: '32px' }}>
                            <label style={{ fontSize: '14px', fontWeight: '600', color: 'var(--text-secondary)' }}>PASSWORD</label>
                            <input
                                className="auth-input"
                                type="password"
                                placeholder="••••••••"
                                value={password}
                                onChange={(e) => setPassword(e.target.value)}
                                required
                            />
                        </div>

                        <button className="auth-btn" type="submit" disabled={loading}>
                            {loading ? 'Processing...' : (isLogin ? 'Sign In to Dashboard' : 'Create My Account')}
                        </button>

                        <div style={{ margin: '24px 0', textAlign: 'center', color: 'var(--text-secondary)', fontSize: '14px', position: 'relative' }}>
                            <span style={{ background: 'var(--bg-card)', padding: '0 10px', position: 'relative', zIndex: '1' }}>or continue with</span>
                            <div style={{ position: 'absolute', top: '50%', left: '0', right: '0', height: '1px', background: 'var(--glass-border)' }}></div>
                        </div>

                        <GoogleSignInButton onSuccess={handleGoogleSuccess} disabled={loading} />
                    </form>

                    {error && <div style={{ marginTop: '20px', padding: '12px', background: 'rgba(239, 68, 68, 0.1)', border: '1px solid rgba(239, 68, 68, 0.2)', borderRadius: '8px', color: '#fca5a5', fontSize: '14px', textAlign: 'center' }}>{error}</div>}
                    {successMsg && <div style={{ marginTop: '20px', padding: '12px', background: 'rgba(34, 211, 238, 0.1)', border: '1px solid rgba(34, 211, 238, 0.2)', borderRadius: '8px', color: '#67e8f9', fontSize: '14px', textAlign: 'center' }}>{successMsg}</div>}

                    <p style={{ marginTop: '32px', textAlign: 'center', fontSize: '14px', color: 'var(--text-secondary)' }}>
                        {isLogin ? "Don't have an account?" : "Already member?"}
                        <span
                            onClick={() => setIsLogin(!isLogin)}
                            style={{ color: 'var(--accent-cyan)', fontWeight: '700', cursor: 'pointer', marginLeft: '5px' }}
                        >
                            {isLogin ? 'Register now' : 'Log in instead'}
                        </span>
                    </p>
                </div>
            </div>
        </div>
    );
}

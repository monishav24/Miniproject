/**
 * SmartV2X-CP Ultra — Login & Register Component
 * Features animated V2X-themed background with road network,
 * moving vehicles, radar pulses, Google Sign-In, and
 * V2X capability showcase with dynamic animations.
 */
import React, { useState, useEffect, useCallback, useRef } from 'react';
import { login as apiLogin, register as apiRegister, googleLogin as apiGoogleLogin } from '../api/auth';
import { useAuth } from '../context/AuthContext';

/* ─── V2X Feature Showcase Data ──────────────────────────── */
const V2X_FEATURES = [
    { icon: '🧠', label: 'LSTM+GRU Neural Network', desc: 'Real-time collision prediction' },
    { icon: '📡', label: 'Extended Kalman Filter', desc: 'GPS + IMU + Radar fusion' },
    { icon: '🗺️', label: 'Collision Probability Map', desc: 'Spatial grid risk analysis' },
    { icon: '🤖', label: 'Reinforcement Learning', desc: 'Smart warning dissemination' },
    { icon: '🔐', label: 'JWT + RBAC Security', desc: 'Multi-service authentication' },
    { icon: '🚗', label: 'Hardware-Ready OBU', desc: 'Sensor abstraction layer' },
    { icon: '📊', label: 'Live Dashboard', desc: 'WebSocket real-time updates' },
];

/* ─── Animated Background ─────────────────────────────────── */
function AnimatedBackground() {
    return (
        <div className="v2x-bg">
            {/* Road grid */}
            <div className="road-grid">
                <div className="road road-h road-h1" />
                <div className="road road-h road-h2" />
                <div className="road road-h road-h3" />
                <div className="road road-v road-v1" />
                <div className="road road-v road-v2" />
                <div className="road road-v road-v3" />
            </div>

            {/* Moving vehicles */}
            <div className="vehicles-layer">
                <div className="vehicle vehicle-1">🚗</div>
                <div className="vehicle vehicle-2">🚙</div>
                <div className="vehicle vehicle-3">🚕</div>
                <div className="vehicle vehicle-4">🏎️</div>
                <div className="vehicle vehicle-5">🚐</div>
                <div className="vehicle vehicle-6">🚗</div>
            </div>

            {/* Radar / Communication pulses */}
            <div className="pulse-layer">
                <div className="radar-pulse rp1" />
                <div className="radar-pulse rp2" />
                <div className="radar-pulse rp3" />
                <div className="radar-pulse rp4" />
            </div>

            {/* Floating particles (map pins, signals) */}
            <div className="particles-layer">
                {Array.from({ length: 20 }).map((_, i) => (
                    <div
                        key={i}
                        className={`particle particle-${(i % 4) + 1}`}
                        style={{
                            left: `${Math.random() * 100}%`,
                            top: `${Math.random() * 100}%`,
                            animationDelay: `${Math.random() * 8}s`,
                            animationDuration: `${6 + Math.random() * 6}s`,
                        }}
                    />
                ))}
            </div>

            {/* V2X connection lines */}
            <svg className="connection-lines" viewBox="0 0 1920 1080" preserveAspectRatio="none">
                <line x1="200" y1="300" x2="600" y2="500" className="conn-line cl1" />
                <line x1="800" y1="200" x2="1200" y2="600" className="conn-line cl2" />
                <line x1="400" y1="700" x2="1000" y2="300" className="conn-line cl3" />
                <line x1="1400" y1="400" x2="1700" y2="800" className="conn-line cl4" />
                <line x1="300" y1="100" x2="900" y2="900" className="conn-line cl5" />
            </svg>

            {/* Gradient overlay for depth */}
            <div className="bg-gradient-overlay" />
        </div>
    );
}

/* ─── V2X Feature Carousel ────────────────────────────────── */
function FeatureShowcase() {
    const [activeIndex, setActiveIndex] = useState(0);

    useEffect(() => {
        const timer = setInterval(() => {
            setActiveIndex((prev) => (prev + 1) % V2X_FEATURES.length);
        }, 3000);
        return () => clearInterval(timer);
    }, []);

    return (
        <div className="feature-showcase">
            <div className="feature-showcase-header">
                <div className="signal-wave">
                    <span className="wave-bar" style={{ animationDelay: '0s' }} />
                    <span className="wave-bar" style={{ animationDelay: '0.15s' }} />
                    <span className="wave-bar" style={{ animationDelay: '0.3s' }} />
                    <span className="wave-bar" style={{ animationDelay: '0.45s' }} />
                    <span className="wave-bar" style={{ animationDelay: '0.6s' }} />
                </div>
                <span className="showcase-label">V2X CAPABILITIES</span>
                <div className="signal-wave">
                    <span className="wave-bar" style={{ animationDelay: '0.6s' }} />
                    <span className="wave-bar" style={{ animationDelay: '0.45s' }} />
                    <span className="wave-bar" style={{ animationDelay: '0.3s' }} />
                    <span className="wave-bar" style={{ animationDelay: '0.15s' }} />
                    <span className="wave-bar" style={{ animationDelay: '0s' }} />
                </div>
            </div>
            <div className="feature-carousel">
                {V2X_FEATURES.map((feat, i) => (
                    <div
                        key={i}
                        className={`feature-item ${i === activeIndex ? 'active' : ''}`}
                    >
                        <span className="feature-icon">{feat.icon}</span>
                        <div className="feature-text">
                            <span className="feature-label">{feat.label}</span>
                            <span className="feature-desc">{feat.desc}</span>
                        </div>
                    </div>
                ))}
            </div>
            {/* Progress dots */}
            <div className="feature-dots">
                {V2X_FEATURES.map((_, i) => (
                    <span
                        key={i}
                        className={`feature-dot ${i === activeIndex ? 'active' : ''}`}
                        onClick={() => setActiveIndex(i)}
                    />
                ))}
            </div>
        </div>
    );
}

/* ─── Neural Network Logo ─────────────────────────────────── */
function NeuralNetworkIcon() {
    return (
        <div className="neural-logo">
            <svg viewBox="0 0 60 60" fill="none" xmlns="http://www.w3.org/2000/svg">
                <defs>
                    <linearGradient id="neuralGrad" x1="0" y1="0" x2="60" y2="60">
                        <stop stopColor="#3b82f6" />
                        <stop offset="1" stopColor="#06b6d4" />
                    </linearGradient>
                </defs>
                <rect width="60" height="60" rx="16" fill="url(#neuralGrad)" />
                {/* Neural network nodes */}
                <circle cx="15" cy="18" r="3.5" fill="white" opacity="0.9" className="nn-node nn-n1" />
                <circle cx="15" cy="30" r="3.5" fill="white" opacity="0.9" className="nn-node nn-n2" />
                <circle cx="15" cy="42" r="3.5" fill="white" opacity="0.9" className="nn-node nn-n3" />
                <circle cx="30" cy="22" r="3.5" fill="white" opacity="0.85" className="nn-node nn-n4" />
                <circle cx="30" cy="38" r="3.5" fill="white" opacity="0.85" className="nn-node nn-n5" />
                <circle cx="45" cy="30" r="4" fill="white" opacity="0.95" className="nn-node nn-n6" />
                {/* Connections */}
                <line x1="18" y1="18" x2="27" y2="22" stroke="white" strokeWidth="1" opacity="0.4" className="nn-conn" />
                <line x1="18" y1="18" x2="27" y2="38" stroke="white" strokeWidth="1" opacity="0.3" className="nn-conn" />
                <line x1="18" y1="30" x2="27" y2="22" stroke="white" strokeWidth="1" opacity="0.4" className="nn-conn" />
                <line x1="18" y1="30" x2="27" y2="38" stroke="white" strokeWidth="1" opacity="0.4" className="nn-conn" />
                <line x1="18" y1="42" x2="27" y2="22" stroke="white" strokeWidth="1" opacity="0.3" className="nn-conn" />
                <line x1="18" y1="42" x2="27" y2="38" stroke="white" strokeWidth="1" opacity="0.4" className="nn-conn" />
                <line x1="33" y1="22" x2="42" y2="30" stroke="white" strokeWidth="1" opacity="0.5" className="nn-conn" />
                <line x1="33" y1="38" x2="42" y2="30" stroke="white" strokeWidth="1" opacity="0.5" className="nn-conn" />
            </svg>
        </div>
    );
}

/* ─── Google Sign-In Button ───────────────────────────────── */
function GoogleSignInButton({ onSuccess, disabled }) {
    const buttonRef = useRef(null);

    useEffect(() => {
        if (window.google?.accounts?.id) {
            initGoogleButton();
            return;
        }

        const existingScript = document.querySelector('script[src*="accounts.google.com/gsi/client"]');
        if (!existingScript) {
            const script = document.createElement('script');
            script.src = 'https://accounts.google.com/gsi/client';
            script.async = true;
            script.defer = true;
            script.onload = () => {
                setTimeout(initGoogleButton, 300);
            };
            document.head.appendChild(script);
        } else {
            const check = setInterval(() => {
                if (window.google?.accounts?.id) {
                    clearInterval(check);
                    initGoogleButton();
                }
            }, 200);
            return () => clearInterval(check);
        }
    }, []);

    function initGoogleButton() {
        if (!window.google?.accounts?.id || !buttonRef.current) return;
        try {
            window.google.accounts.id.initialize({
                client_id: import.meta.env.VITE_GOOGLE_CLIENT_ID || '000000000000-placeholder.apps.googleusercontent.com',
                callback: handleCredentialResponse,
            });
            window.google.accounts.id.renderButton(buttonRef.current, {
                theme: 'filled_black',
                size: 'large',
                width: 340,
                text: 'continue_with',
                shape: 'pill',
            });
        } catch (err) {
            console.warn('Google Sign-In init error:', err);
        }
    }

    function handleCredentialResponse(response) {
        if (response.credential) {
            onSuccess(response.credential);
        }
    }

    return (
        <div className="google-btn-wrapper">
            <div ref={buttonRef} id="google-signin-btn" />
            <button
                type="button"
                className="google-btn-fallback"
                onClick={() => {
                    alert('Google Sign-In requires a valid VITE_GOOGLE_CLIENT_ID in your .env file');
                }}
                disabled={disabled}
            >
                <svg className="google-icon" viewBox="0 0 24 24" width="20" height="20">
                    <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 01-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z" fill="#4285F4" />
                    <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853" />
                    <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05" />
                    <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335" />
                </svg>
                Continue with Google
            </button>
        </div>
    );
}

/* ─── Main Login/Register Component ───────────────────────── */
export default function Login() {
    const { login } = useAuth();
    const [isLogin, setIsLogin] = useState(true);
    const [username, setUsername] = useState('');
    const [password, setPassword] = useState('');
    const [name, setName] = useState('');
    const [error, setError] = useState('');
    const [loading, setLoading] = useState(false);
    const [successMsg, setSuccessMsg] = useState('');
    const [formKey, setFormKey] = useState(0); // triggers re-animation on mode switch

    const handleSubmit = async (e) => {
        e.preventDefault();
        setError('');
        setSuccessMsg('');
        setLoading(true);
        try {
            if (isLogin) {
                const data = await apiLogin(username, password);
                login(data);
            } else {
                const data = await apiRegister(username, password, name);
                setSuccessMsg('Account created! Logging you in...');
                setTimeout(() => login(data), 800);
            }
        } catch (err) {
            setError(err.message || 'Authentication failed');
        } finally {
            setLoading(false);
        }
    };

    const handleGoogleSuccess = useCallback(async (idToken) => {
        setError('');
        setLoading(true);
        try {
            const data = await apiGoogleLogin(idToken);
            setSuccessMsg('Welcome! Signing you in...');
            setTimeout(() => login(data), 600);
        } catch (err) {
            setError(err.message || 'Google sign-in failed');
        } finally {
            setLoading(false);
        }
    }, [login]);

    const toggleMode = () => {
        setIsLogin(!isLogin);
        setError('');
        setSuccessMsg('');
        setUsername('');
        setPassword('');
        setName('');
        setFormKey((k) => k + 1); // re-trigger stagger animation
    };

    return (
        <div className="login-container">
            {/* Animated Background */}
            <AnimatedBackground />

            {/* Login Card */}
            <form className="login-card" onSubmit={handleSubmit}>
                {/* Neural Network Logo & Header */}
                <div className="login-logo">
                    <NeuralNetworkIcon />
                    <h1>SmartV2X-CP</h1>
                    <p className="login-tagline">
                        AI-Powered Collision Prediction System
                    </p>
                </div>

                {/* V2X Feature Showcase */}
                <FeatureShowcase />

                <p className="subtitle">
                    {isLogin ? 'Sign in to access the platform' : 'Create your account to get started'}
                </p>

                {/* Google Sign-In */}
                <GoogleSignInButton onSuccess={handleGoogleSuccess} disabled={loading} />

                {/* Divider */}
                <div className="auth-divider">
                    <span>or {isLogin ? 'sign in' : 'register'} with credentials</span>
                </div>

                {/* Staggered Form Fields */}
                <div className="form-fields-animated" key={formKey}>
                    {/* Name field (Register only) */}
                    {!isLogin && (
                        <div className="form-group stagger-field" style={{ animationDelay: '0.05s' }}>
                            <label htmlFor="name">Primary Vehicle Name</label>
                            <div className="input-wrapper">
                                <span className="input-icon">🚗</span>
                                <input
                                    id="name"
                                    type="text"
                                    value={name}
                                    onChange={(e) => setName(e.target.value)}
                                    placeholder="e.g. Tesla Model 3"
                                />
                            </div>
                        </div>
                    )}

                    <div className="form-group stagger-field" style={{ animationDelay: isLogin ? '0.05s' : '0.15s' }}>
                        <label htmlFor="username">Username</label>
                        <div className="input-wrapper">
                            <span className="input-icon">📧</span>
                            <input
                                id="username"
                                type="text"
                                value={username}
                                onChange={(e) => setUsername(e.target.value)}
                                placeholder="Enter username"
                                autoComplete="username"
                                required
                            />
                        </div>
                    </div>

                    <div className="form-group stagger-field" style={{ animationDelay: isLogin ? '0.15s' : '0.25s' }}>
                        <label htmlFor="password">Password</label>
                        <div className="input-wrapper">
                            <span className="input-icon">🔒</span>
                            <input
                                id="password"
                                type="password"
                                value={password}
                                onChange={(e) => setPassword(e.target.value)}
                                placeholder="Enter password"
                                autoComplete={isLogin ? "current-password" : "new-password"}
                                required
                            />
                        </div>
                    </div>

                    <button className="btn-primary stagger-field" type="submit" disabled={loading}
                        style={{ animationDelay: isLogin ? '0.25s' : '0.35s' }}>
                        {loading ? (
                            <span className="btn-loading">
                                <span className="spinner" />
                                Processing…
                            </span>
                        ) : (
                            isLogin ? '🚀 Sign In' : '✨ Create Account'
                        )}
                    </button>
                </div>

                {error && <p className="login-error">{error}</p>}
                {successMsg && <p className="login-success">{successMsg}</p>}

                <div className="login-footer">
                    <p>
                        {isLogin ? "Don't have an account? " : "Already have an account? "}
                        <button type="button" onClick={toggleMode} className="link-btn">
                            {isLogin ? 'Sign Up' : 'Log In'}
                        </button>
                    </p>
                </div>

                {/* Feature badges */}
                <div className="login-features">
                    <span className="feature-badge fb-1">🛡️ V2X Secured</span>
                    <span className="feature-badge fb-2">⚡ Real-time</span>
                    <span className="feature-badge fb-3">🤖 AI-Powered</span>
                </div>
            </form>
        </div>
    );
}

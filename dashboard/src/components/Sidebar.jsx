import React from 'react';
import { useAuth } from '../context/AuthContext';

export default function Sidebar() {
    const { logout, user } = useAuth();

    return (
        <aside className="glass" style={{ width: '280px', height: '100vh', position: 'sticky', top: 0, padding: '32px', display: 'flex', flexDirection: 'column', borderLeft: 'none', borderRadius: '0 24px 24px 0' }}>
            <div style={{ marginBottom: '48px', display: 'flex', alignItems: 'center', gap: '12px' }}>
                <div style={{ width: '40px', height: '40px', background: 'var(--accent-cyan)', borderRadius: '10px', display: 'flex', alignItems: 'center', justifyCenter: 'center', fontWeight: '800', color: 'var(--bg-deep-blue)', fontSize: '20px' }}>V</div>
                <h2 style={{ fontSize: '20px', fontWeight: '800', letterSpacing: '-0.5px' }}>SmartV2X</h2>
            </div>

            <nav style={{ flex: 1 }}>
                <ul style={{ listStyle: 'none', padding: 0 }}>
                    <li style={{ marginBottom: '12px' }}>
                        <div style={{ padding: '12px 16px', borderRadius: '12px', background: 'rgba(34, 211, 238, 0.1)', color: 'var(--accent-cyan)', fontWeight: '600', display: 'flex', alignItems: 'center', gap: '12px', cursor: 'pointer' }}>
                            <span>📊</span> Dashboard
                        </div>
                    </li>
                    <li style={{ marginBottom: '12px' }}>
                        <div style={{ padding: '12px 16px', borderRadius: '12px', color: 'var(--text-secondary)', fontWeight: '600', display: 'flex', alignItems: 'center', gap: '12px', cursor: 'pointer', transition: 'var(--transition-smooth)' }}>
                            <span>🚗</span> Vehicles
                        </div>
                    </li>
                    <li style={{ marginBottom: '12px' }}>
                        <div style={{ padding: '12px 16px', borderRadius: '12px', color: 'var(--text-secondary)', fontWeight: '600', display: 'flex', alignItems: 'center', gap: '12px', cursor: 'pointer', transition: 'var(--transition-smooth)' }}>
                            <span>🛡️</span> Security
                        </div>
                    </li>
                    <li style={{ marginBottom: '12px' }}>
                        <div style={{ padding: '12px 16px', borderRadius: '12px', color: 'var(--text-secondary)', fontWeight: '600', display: 'flex', alignItems: 'center', gap: '12px', cursor: 'pointer', transition: 'var(--transition-smooth)' }}>
                            <span>⚙️</span> Settings
                        </div>
                    </li>
                </ul>
            </nav>

            <div style={{ marginTop: 'auto', paddingTop: '24px', borderTop: '1px solid var(--glass-border)' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '20px' }}>
                    <div style={{ width: '40px', height: '40px', background: 'var(--glass-border)', borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '18px' }}>👤</div>
                    <div>
                        <div style={{ fontSize: '14px', fontWeight: '700' }}>{user?.username || 'Fleet Manager'}</div>
                        <div style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>Admin Status</div>
                    </div>
                </div>
                <button
                    onClick={logout}
                    style={{ width: '100%', padding: '12px', borderRadius: '12px', background: 'rgba(239, 68, 68, 0.1)', color: '#fca5a5', border: '1px solid rgba(239, 68, 68, 0.2)', fontWeight: '600', cursor: 'pointer', transition: 'var(--transition-smooth)' }}
                >
                    Logout Session
                </button>
            </div>
        </aside>
    );
}

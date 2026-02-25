/**
 * SmartV2X-CP Ultra — Vehicle Pairing Status
 * Premium hover-reactive cards with live telemetry data.
 */
import React from 'react';

export default function PairingStatus({ vehicles = {} }) {
    const list = Object.values(vehicles);

    if (list.length === 0) {
        return (
            <div style={{ textAlign: 'center', padding: '40px', background: 'rgba(255,255,255,0.02)', borderRadius: '20px', border: '1px dashed var(--glass-border)' }}>
                <div style={{ fontSize: '40px', marginBottom: '16px' }}>🚗</div>
                <p style={{ fontWeight: '700', marginBottom: '4px' }}>Fleet is empty</p>
                <p style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>Pair an OBU to start live V2X monitoring</p>
            </div>
        );
    }

    return (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            {list.map((v) => {
                const isOnline = v.last_telemetry && (new Date() - new Date(v.last_telemetry.timestamp)) < 15000;
                const riskProb = v.last_telemetry?.collision_probability || 0;
                const riskLevel = riskProb > 0.6 ? 'HIGH' : riskProb > 0.3 ? 'MEDIUM' : 'LOW';
                const riskColor = riskLevel === 'HIGH' ? '#fca5a5' : riskLevel === 'MEDIUM' ? '#fcd34d' : '#67e8f9';

                return (
                    <div
                        key={v.id}
                        className="glass"
                        style={{
                            padding: '20px',
                            display: 'flex',
                            alignItems: 'center',
                            gap: '20px',
                            transition: 'var(--transition-smooth)',
                            cursor: 'pointer',
                            position: 'relative',
                            overflow: 'hidden'
                        }}
                        onMouseEnter={(e) => {
                            e.currentTarget.style.transform = 'translateX(8px)';
                            e.currentTarget.style.borderColor = 'var(--accent-cyan)';
                            e.currentTarget.style.background = 'rgba(34, 211, 238, 0.05)';
                        }}
                        onMouseLeave={(e) => {
                            e.currentTarget.style.transform = 'translateX(0)';
                            e.currentTarget.style.borderColor = 'var(--glass-border)';
                            e.currentTarget.style.background = 'var(--bg-card)';
                        }}
                    >
                        {/* Status Pulse */}
                        <div style={{ position: 'relative', width: '48px', height: '48px', borderRadius: '12px', background: isOnline ? 'rgba(34, 211, 238, 0.1)' : 'rgba(255,255,255,0.05)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '20px' }}>
                            {isOnline ? '📡' : '💤'}
                            {isOnline && <div style={{ position: 'absolute', top: -2, right: -2, width: '10px', height: '10px', background: 'var(--accent-cyan)', borderRadius: '50%', boxShadow: '0 0 10px var(--accent-cyan)' }} />}
                        </div>

                        <div style={{ flex: 1 }}>
                            <div style={{ fontSize: '15px', fontWeight: '800', marginBottom: '4px' }}>{v.name}</div>
                            <div style={{ fontSize: '12px', color: 'var(--text-secondary)', display: 'flex', alignItems: 'center', gap: '6px' }}>
                                <span style={{ width: '6px', height: '6px', borderRadius: '50%', background: isOnline ? 'var(--accent-cyan)' : '#94a3b8' }} />
                                {isOnline ? 'ACTIVE SESSION' : 'OFFLINE'}
                            </div>
                        </div>

                        <div style={{ textAlign: 'right' }}>
                            <div style={{ fontSize: '18px', fontWeight: '800', color: 'var(--accent-cyan)' }}>
                                {v.last_telemetry?.speed || 0}<span style={{ fontSize: '10px', marginLeft: '2px' }}>KM/H</span>
                            </div>
                            <div style={{ fontSize: '11px', fontWeight: '700', color: riskColor, textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                                {riskLevel} RISK
                            </div>
                        </div>
                    </div>
                );
            })}
        </div>
    );
}

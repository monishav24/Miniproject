/**
 * SmartV2X-CP Ultra — Alert Panel
 * Premium glassmorphism collision feed with risk indicators.
 */
import React from 'react';

export default function AlertPanel({ alerts = [] }) {
    if (alerts.length === 0) {
        return (
            <div style={{ textAlign: 'center', padding: '32px', color: 'var(--text-secondary)' }}>
                <div style={{ fontSize: '32px', marginBottom: '12px' }}>🛡️</div>
                <p style={{ fontSize: '14px', fontWeight: '600' }}>No active threats detected</p>
            </div>
        );
    }

    return (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            {alerts.map((alert, idx) => {
                const level = (alert.risk?.level || 'LOW').toUpperCase();
                const color = level === 'HIGH' ? '#fca5a5' : level === 'MEDIUM' ? '#fcd34d' : 'var(--accent-cyan)';

                return (
                    <div key={idx} style={{
                        padding: '16px',
                        background: 'rgba(255,255,255,0.02)',
                        border: '1px solid var(--glass-border)',
                        borderRadius: '12px',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '16px',
                        animation: 'slideFadeIn 0.5s ease-out both',
                        animationDelay: `${idx * 0.05}s`
                    }}>
                        <div style={{ fontSize: '20px' }}>
                            {level === 'HIGH' ? '🚨' : level === 'MEDIUM' ? '⚠️' : 'ℹ️'}
                        </div>
                        <div style={{ flex: 1 }}>
                            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
                                <span style={{ fontSize: '13px', fontWeight: '800', color }}>{level} RISK</span>
                                <span style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>
                                    {alert.timestamp ? new Date(alert.timestamp * 1000).toLocaleTimeString() : 'Just now'}
                                </span>
                            </div>
                            <div style={{ fontSize: '13px', fontWeight: '600' }}>{alert.vehicle_id || 'Global Event'}</div>
                            <div style={{ fontSize: '11px', color: 'var(--text-secondary)', marginTop: '4px' }}>
                                Probability: {((alert.risk?.score || 0) * 100).toFixed(0)}% • TTC: {alert.risk?.ttc?.toFixed(1) || '0.0'}s
                            </div>
                        </div>
                    </div>
                );
            })}
        </div>
    );
}

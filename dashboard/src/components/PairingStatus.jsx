/**
 * SmartV2X-CP Ultra — Vehicle Pairing Status
 */
import React from 'react';

export default function PairingStatus({ vehicles = {} }) {
    const list = Object.values(vehicles);

    if (list.length === 0) {
        return (
            <div className="empty-state">
                <div className="icon">🚗</div>
                <p>No vehicles paired</p>
                <p style={{ fontSize: 12 }}>Waiting for OBU connections</p>
            </div>
        );
    }

    return (
        <div className="vehicle-list">
            {list.map((v) => {
                const isOnline = v.last_telemetry && (new Date() - new Date(v.last_telemetry.timestamp)) < 10000;
                const riskLevel = (v.last_telemetry?.collision_probability > 0.6 ? 'HIGH' : 'LOW');

                return (
                    <div key={v.id} className="vehicle-item">
                        <div className="vehicle-info">
                            <div className={`vehicle-dot ${isOnline ? 'online' : 'offline'}`} />
                            <div>
                                <div className="vehicle-name">{v.name}</div>
                                <div className="vehicle-status">
                                    {isOnline ? 'Live • ' : 'Last seen '}
                                    {v.last_telemetry ? new Date(v.last_telemetry.timestamp).toLocaleTimeString() : 'Never'}
                                </div>
                            </div>
                        </div>
                        <div className="vehicle-metrics" style={{ marginLeft: 'auto', textAlign: 'right', marginRight: '15px' }}>
                            <div style={{ color: 'var(--accent-cyan)', fontWeight: 'bold' }}>
                                {v.last_telemetry ? `${v.last_telemetry.speed} km/h` : '0 km/h'}
                            </div>
                            <div style={{ fontSize: '10px', color: 'var(--text-secondary)' }}>Speed</div>
                        </div>
                        <span className={`risk-badge ${riskLevel.toLowerCase()}`}>
                            {riskLevel}
                        </span>
                    </div>
                );
            })}
        </div>
    );
}

/**
 * SmartV2X-CP Ultra — Alert Panel
 * Collision alerts with risk-level-based entrance animations.
 */
import React from 'react';

export default function AlertPanel({ alerts = [] }) {
    if (alerts.length === 0) {
        return (
            <div className="empty-state">
                <div className="icon">🛡️</div>
                <p>No collision alerts — all clear!</p>
            </div>
        );
    }

    return (
        <div className="alert-list" style={{ maxHeight: 300, overflowY: 'auto' }}>
            {alerts.map((alert, idx) => {
                const level = (alert.risk?.level || 'LOW').toUpperCase();
                const animClass =
                    level === 'HIGH' ? 'alert-enter-high' :
                        level === 'MEDIUM' ? 'alert-enter-medium' : 'alert-enter-low';

                return (
                    <div key={idx} className={`alert-item ${animClass}`}
                        style={{ animationDelay: `${idx * 0.05}s` }}>
                        <div className={`alert-icon ${level.toLowerCase()}`}>
                            {level === 'HIGH' ? '🚨' : level === 'MEDIUM' ? '⚠️' : 'ℹ️'}
                        </div>
                        <div className="alert-content">
                            <div className="title">
                                {level} Risk — {alert.vehicle_id || 'Unknown'}
                            </div>
                            <div className="details">
                                Score: {alert.risk?.score?.toFixed(3) || 'N/A'}
                                {alert.risk?.ttc != null && ` • TTC: ${alert.risk.ttc.toFixed(1)}s`}
                            </div>
                            <div className="time">
                                {alert.timestamp
                                    ? new Date(alert.timestamp * 1000).toLocaleTimeString()
                                    : 'Just now'}
                            </div>
                        </div>
                    </div>
                );
            })}
        </div>
    );
}

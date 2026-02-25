/**
 * SmartV2X-CP Ultra — System Health Panel
 * Animated stat cards with pulse effects and counting animation.
 */
import React, { useState, useEffect, useRef } from 'react';

function AnimVal({ value, suffix = '' }) {
    const [display, setDisplay] = useState(0);
    const prevRef = useRef(0);

    useEffect(() => {
        const start = prevRef.current;
        const end = typeof value === 'number' ? value : 0;
        if (start === end) { setDisplay(end); return; }
        const startTime = Date.now();
        const tick = () => {
            const progress = Math.min((Date.now() - startTime) / 800, 1);
            const eased = 1 - Math.pow(1 - progress, 3);
            setDisplay(Math.round(start + (end - start) * eased));
            if (progress < 1) requestAnimationFrame(tick);
            else prevRef.current = end;
        };
        requestAnimationFrame(tick);
    }, [value]);

    return <>{display}{suffix}</>;
}

export default function HealthPanel({ health = {}, vehicleCount = 0 }) {
    const uptime = health.uptime_seconds
        ? `${Math.floor(health.uptime_seconds / 3600)}h ${Math.floor((health.uptime_seconds % 3600) / 60)}m`
        : '—';

    const isHealthy = health.status === 'healthy';

    return (
        <div className="stats-grid">
            <div className="stat-card stat-animate" style={{ animationDelay: '0.05s' }}>
                <div className="label">Status</div>
                <div className={`value ${isHealthy ? 'green' : 'red'}`}>
                    <span className={isHealthy ? 'status-dot-pulse green' : 'status-dot-pulse red'} />
                    {isHealthy ? ' Healthy' : ' Down'}
                </div>
            </div>
            <div className="stat-card stat-animate" style={{ animationDelay: '0.1s' }}>
                <div className="label">Uptime</div>
                <div className="value cyan">{uptime}</div>
            </div>
            <div className="stat-card stat-animate" style={{ animationDelay: '0.15s' }}>
                <div className="label">Active Vehicles</div>
                <div className="value blue">
                    <AnimVal value={health.active_vehicles ?? vehicleCount} />
                </div>
            </div>
            <div className="stat-card stat-animate" style={{ animationDelay: '0.2s' }}>
                <div className="label">Total Vehicles</div>
                <div className="value purple">
                    <AnimVal value={health.total_vehicles ?? 0} />
                </div>
            </div>
            <div className="stat-card stat-animate" style={{ animationDelay: '0.25s' }}>
                <div className="label">Collision Events</div>
                <div className="value amber">
                    <AnimVal value={health.collision_events_total ?? 0} />
                </div>
            </div>
            <div className="stat-card stat-animate" style={{ animationDelay: '0.3s' }}>
                <div className="label">Server Latency</div>
                <div className="value green">&lt; 60ms</div>
            </div>
        </div>
    );
}

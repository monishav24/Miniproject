/**
 * SmartV2X-CP Ultra — Dashboard Page
 * Main dashboard view with cascading panel animations, animated counters,
 * live data flow indicators, and AI analytics integration.
 */
import React, { useState, useEffect, useRef, useCallback } from 'react';
import { useAuth } from '../context/AuthContext';
import { V2XWebSocket } from '../api/websocket';
import { authHeaders } from '../api/auth';
import VehicleMap from '../components/VehicleMap';
import AlertPanel from '../components/AlertPanel';
import LatencyGraph from '../components/LatencyGraph';
import HealthPanel from '../components/HealthPanel';
import PairingStatus from '../components/PairingStatus';

const API_URL = import.meta.env.VITE_API_URL || '';

/* ─── Animated Counter Component ──────────────────────────── */
function AnimatedCounter({ value, duration = 1200, prefix = '', suffix = '' }) {
    const [display, setDisplay] = useState(0);
    const prevRef = useRef(0);

    useEffect(() => {
        const start = prevRef.current;
        const end = typeof value === 'number' ? value : 0;
        if (start === end) return;

        const startTime = Date.now();
        const tick = () => {
            const elapsed = Date.now() - startTime;
            const progress = Math.min(elapsed / duration, 1);
            // Ease-out cubic
            const eased = 1 - Math.pow(1 - progress, 3);
            const current = Math.round(start + (end - start) * eased);
            setDisplay(current);
            if (progress < 1) requestAnimationFrame(tick);
            else prevRef.current = end;
        };
        requestAnimationFrame(tick);
    }, [value, duration]);

    return <>{prefix}{display}{suffix}</>;
}

/* ─── Data Flow Indicator ─────────────────────────────────── */
function DataFlowIndicator() {
    return (
        <div className="data-flow-indicator">
            <span className="df-dot" style={{ animationDelay: '0s' }} />
            <span className="df-dot" style={{ animationDelay: '0.2s' }} />
            <span className="df-dot" style={{ animationDelay: '0.4s' }} />
            <span className="df-label">Data Flow</span>
        </div>
    );
}

/* ─── AI Insights Panel ───────────────────────────────────── */
function AIInsightsPanel() {
    const [insights, setInsights] = useState(null);

    useEffect(() => {
        const fetchInsights = async () => {
            try {
                const resp = await fetch(`${API_URL}/backend/api/dashboard/summary`, {
                    headers: authHeaders(),
                });
                if (resp.ok) setInsights(await resp.json());
            } catch { /* ignore */ }
        };
        fetchInsights();
        const interval = setInterval(fetchInsights, 10000);
        return () => clearInterval(interval);
    }, []);

    return (
        <div className="ai-insights-content">
            <div className="stats-grid">
                <div className="stat-card ai-stat">
                    <div className="label">Vehicle Fleet</div>
                    <div className="value cyan">
                        <AnimatedCounter value={insights?.vehicle_count} />
                    </div>
                </div>
                <div className="stat-card ai-stat">
                    <div className="label">Telemetry Points</div>
                    <div className="value blue">
                        <AnimatedCounter value={insights?.total_telemetry} />
                    </div>
                </div>
                <div className="stat-card ai-stat">
                    <div className="label">Avg Safety Score</div>
                    <div className="value green">
                        {insights?.avg_unsafe_score ?? '0.00'}
                    </div>
                    <div className="stat-bar">
                        <div className="stat-bar-fill green-fill"
                            style={{ width: `${Math.min(100, (insights?.avg_unsafe_score || 0))}%` }} />
                    </div>
                </div>
                <div className="stat-card ai-stat">
                    <div className="label">Last Sync</div>
                    <div className="value purple" style={{ fontSize: '12px' }}>
                        {insights?.last_communication ? new Date(insights.last_communication).toLocaleTimeString() : 'Never'}
                    </div>
                </div>
            </div>
            {data?.insights && (
                <div className="ai-insights-list">
                    {data.insights.slice(0, 3).map((insight, i) => (
                        <div key={i} className="ai-insight-item" style={{ animationDelay: `${i * 0.15}s` }}>
                            <span className="ai-insight-dot" />
                            <span>{insight}</span>
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
}

export default function Dashboard() {
    const { user, logout } = useAuth();
    const [vehicles, setVehicles] = useState({});
    const [vehicleLocations, setVehicleLocations] = useState([]);
    const [alerts, setAlerts] = useState([]);
    const [latencyData, setLatencyData] = useState([]);
    const [health, setHealth] = useState({});
    const [wsConnected, setWsConnected] = useState(false);
    const [uptimeStr, setUptimeStr] = useState('0:00:00');
    const wsRef = useRef(null);
    const startTimeRef = useRef(Date.now());

    // Runtime clock
    useEffect(() => {
        const tick = setInterval(() => {
            const elapsed = Math.floor((Date.now() - startTimeRef.current) / 1000);
            const h = Math.floor(elapsed / 3600);
            const m = Math.floor((elapsed % 3600) / 60);
            const s = elapsed % 60;
            setUptimeStr(`${h}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`);
        }, 1000);
        return () => clearInterval(tick);
    }, []);

    // WebSocket message handler
    const handleWSMessage = useCallback((msg) => {
        if (msg.type === 'vehicle_update') {
            setVehicles((prev) => ({
                ...prev,
                [msg.vehicle_id]: { vehicle_id: msg.vehicle_id, ...msg.data },
            }));

            if (msg.timestamp) {
                const latency = (Date.now() / 1000 - msg.timestamp) * 1000;
                setLatencyData((prev) => [...prev.slice(-59), Math.max(0, latency)]);
            }

            const level = msg.data?.risk?.level;
            if (level === 'HIGH' || level === 'MEDIUM') {
                setAlerts((prev) => [
                    { vehicle_id: msg.vehicle_id, risk: msg.data.risk, timestamp: msg.timestamp },
                    ...prev.slice(0, 49),
                ]);
            }
        }

        if (msg.type === 'alert') {
            setAlerts((prev) => [msg.data, ...prev.slice(0, 49)]);
        }
    }, []);

    // Connect WebSocket
    useEffect(() => {
        wsRef.current = new V2XWebSocket(handleWSMessage, setWsConnected);
        wsRef.current.connect();
        return () => { if (wsRef.current) wsRef.current.disconnect(); };
    }, [handleWSMessage]);

    // Poll health endpoint
    useEffect(() => {
        const fetchHealth = async () => {
            try {
                const resp = await fetch(`${API_URL}/api/health`, { headers: authHeaders() });
                if (resp.ok) setHealth(await resp.json());
            } catch { /* ignore */ }
        };
        fetchHealth();
        const interval = setInterval(fetchHealth, 10000);
        return () => clearInterval(interval);
    }, []);

    // Poll vehicle locations for map
    useEffect(() => {
        const fetchLocations = async () => {
            try {
                const resp = await fetch(`${API_URL}/backend/api/vehicles/locations`, { headers: authHeaders() });
                if (resp.ok) {
                    setVehicleLocations(await resp.json());
                }
            } catch { /* ignore */ }
        };
        fetchLocations();
        const interval = setInterval(fetchLocations, 3000); // 3-second refresh
        return () => clearInterval(interval);
    }, []);

    // Poll vehicle list for pairing status
    useEffect(() => {
        const fetchVehicles = async () => {
            try {
                const resp = await fetch(`${API_URL}/backend/api/vehicles`, { headers: authHeaders() });
                if (resp.ok) {
                    const data = await resp.json();
                    const map = {};
                    (data || []).forEach((v) => { map[v.id] = v; });
                    setVehicles((prev) => ({ ...prev, ...map }));
                }
            } catch { /* ignore */ }
        };
        fetchVehicles();
        const interval = setInterval(fetchVehicles, 10000);
        return () => clearInterval(interval);
    }, []);

    return (
        <div className="dashboard">
            {/* ── Top Bar ───────────────────────────────────── */}
            <header className="topbar topbar-animate">
                <div className="topbar-brand">
                    <div className="logo logo-pulse">V2X</div>
                    <h2>SmartV2X-CP Ultra</h2>
                </div>
                <div className="topbar-center">
                    <DataFlowIndicator />
                    <div className="uptime-display">
                        <span className="uptime-label">SESSION</span>
                        <span className="uptime-value">{uptimeStr}</span>
                    </div>
                </div>
                <div className="topbar-right">
                    <div className="ws-status">
                        <div className={`ws-dot ${wsConnected ? '' : 'disconnected'}`} />
                        {wsConnected ? 'Live' : 'Disconnected'}
                    </div>
                    <div className="user-info">
                        <span>{user?.name || 'User'}</span>
                        <span className="user-role">{user?.role || 'viewer'}</span>
                    </div>
                    <button className="btn-logout" onClick={logout}>
                        Sign Out
                    </button>
                </div>
            </header>

            {/* ── Main Grid ────────────────────────────────── */}
            <div className="dashboard-content">
                {/* Left: Map */}
                <div className="panel map-panel panel-animate" style={{ '--panel-delay': '0.1s' }}>
                    <div className="panel-header">
                        <h3>🗺️ Live Vehicle Map</h3>
                        <span className="badge badge-live pulse-badge">● LIVE</span>
                    </div>
                    <VehicleMap vehicles={vehicleLocations} />
                </div>

                {/* Right: Alerts */}
                <div className="panel panel-animate" style={{ '--panel-delay': '0.2s' }}>
                    <div className="panel-header">
                        <h3>⚠️ Collision Alerts</h3>
                        <span className="badge badge-live pulse-badge">
                            <AnimatedCounter value={alerts.length} />
                        </span>
                    </div>
                    <div className="panel-body">
                        <AlertPanel alerts={alerts} />
                    </div>
                </div>

                {/* Right: Health */}
                <div className="panel panel-animate" style={{ '--panel-delay': '0.3s' }}>
                    <div className="panel-header">
                        <h3>📡 System Health</h3>
                    </div>
                    <div className="panel-body">
                        <HealthPanel health={health} vehicleCount={Object.keys(vehicles).length} />
                    </div>
                </div>

                {/* Bottom Row */}
                <div className="bottom-row">
                    <div className="panel panel-animate" style={{ '--panel-delay': '0.4s' }}>
                        <div className="panel-header">
                            <h3>📊 Network Latency</h3>
                        </div>
                        <LatencyGraph latencyData={latencyData} />
                    </div>

                    <div className="panel panel-animate" style={{ '--panel-delay': '0.5s' }}>
                        <div className="panel-header">
                            <h3>🔗 Vehicle Pairing</h3>
                            <span className="badge badge-live pulse-badge">
                                <AnimatedCounter value={Object.keys(vehicles).length} suffix=" devices" />
                            </span>
                        </div>
                        <div className="panel-body">
                            <PairingStatus vehicles={vehicles} />

                            {/* Add Vehicle Form */}
                            <div className="add-vehicle-form" style={{ marginTop: '20px', padding: '15px', background: 'rgba(255,255,255,0.03)', borderRadius: '12px' }}>
                                <h4 style={{ marginBottom: '10px', fontSize: '14px', color: 'var(--text-secondary)' }}>Register New Vehicle</h4>
                                <div style={{ display: 'flex', gap: '10px' }}>
                                    <input
                                        type="text"
                                        placeholder="Vehicle Name"
                                        id="new-v-name"
                                        style={{ flex: 1, padding: '8px', background: 'rgba(0,0,0,0.2)', border: '1px solid var(--border-glass)', color: 'white', borderRadius: '4px' }}
                                    />
                                    <button
                                        className="btn-primary"
                                        style={{ width: 'auto', padding: '8px 15px', marginTop: 0 }}
                                        onClick={async () => {
                                            const name = document.getElementById('new-v-name').value;
                                            if (!name) return;
                                            try {
                                                const resp = await fetch(`${API_URL}/backend/api/vehicles`, {
                                                    method: 'POST',
                                                    headers: { ...authHeaders(), 'Content-Type': 'application/json' },
                                                    body: JSON.stringify({ name })
                                                });
                                                if (resp.ok) {
                                                    document.getElementById('new-v-name').value = '';
                                                    // Trigger refresh
                                                    window.location.reload();
                                                }
                                            } catch (err) { alert('Failed to add vehicle'); }
                                        }}
                                    >
                                        Add
                                    </button>
                                </div>
                            </div>
                        </div>
                    </div>

                    {/* AI Analytics Panel */}
                    <div className="panel panel-animate ai-panel" style={{ '--panel-delay': '0.6s' }}>
                        <div className="panel-header">
                            <h3>🧠 AI Analytics</h3>
                            <span className="badge badge-ai">AI POWERED</span>
                        </div>
                        <div className="panel-body">
                            <AIInsightsPanel />
                        </div>
                    </div>

                    {/* Admin-only panel */}
                    {user?.role === 'admin' && (
                        <div className="panel panel-animate" style={{ '--panel-delay': '0.7s' }}>
                            <div className="panel-header">
                                <h3>🛠️ Admin Controls</h3>
                            </div>
                            <div className="panel-body">
                                <div className="stats-grid">
                                    <div className="stat-card">
                                        <div className="label">WS Clients</div>
                                        <div className="value cyan">1</div>
                                    </div>
                                    <div className="stat-card">
                                        <div className="label">API Rate</div>
                                        <div className="value green">OK</div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}

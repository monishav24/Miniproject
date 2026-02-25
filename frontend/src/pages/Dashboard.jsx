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
import Sidebar from '../components/Sidebar';

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

/* ─── Simulation Control Panel ───────────────────────────── */
function SimulationPanel() {
    const [status, setStatus] = useState('STOPPED');
    const [loading, setLoading] = useState(false);

    const toggleSim = async () => {
        setLoading(true);
        const endpoint = status === 'STOPPED' ? '/simulation/start' : '/simulation/stop';
        try {
            const resp = await fetch(`${API_URL}${endpoint}`, {
                method: 'POST',
                headers: authHeaders()
            });
            if (resp.ok) {
                const data = await resp.json();
                if (data.status.includes('started')) setStatus('RUNNING');
                else setStatus('STOPPED');
            }
        } catch { /* ignore */ }
        setLoading(false);
    };

    return (
        <div className="glass" style={{ padding: '24px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '16px' }}>
                <h3 style={{ fontSize: '18px', fontWeight: '800' }}>Virtual Traffic Engine</h3>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <div style={{ width: '8px', height: '8px', borderRadius: '50%', background: status === 'RUNNING' ? 'var(--accent-cyan)' : '#64748b', boxShadow: status === 'RUNNING' ? '0 0 10px var(--accent-cyan)' : 'none' }} />
                    <span style={{ fontSize: '11px', fontWeight: '800', color: status === 'RUNNING' ? 'var(--accent-cyan)' : 'var(--text-secondary)' }}>{status}</span>
                </div>
            </div>
            <p style={{ fontSize: '13px', color: 'var(--text-secondary)', marginBottom: '20px' }}>
                Simulate 50+ autonomous vehicles with randomized trajectories and risk profiles.
            </p>
            <button
                onClick={toggleSim}
                disabled={loading}
                className="auth-btn"
                style={{ background: status === 'RUNNING' ? 'rgba(239, 68, 68, 0.1)' : 'rgba(34, 211, 238, 0.1)', border: `1px solid ${status === 'RUNNING' ? '#ef4444' : 'var(--accent-cyan)'}`, color: status === 'RUNNING' ? '#ef4444' : 'var(--accent-cyan)', opacity: loading ? 0.6 : 1 }}
            >
                {loading ? 'Processing...' : status === 'STOPPED' ? 'Launch 50-Vehicle Swarm' : 'Terminate Simulation'}
            </button>
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
                const resp = await fetch(`${API_URL}/edge/api/health`, { headers: authHeaders() });
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
                const resp = await fetch(`${API_URL}/vehicles/locations`, { headers: authHeaders() });
                if (resp.ok) {
                    setVehicleLocations(await resp.json());
                }
            } catch { /* ignore */ }
        };
        fetchLocations();
        const interval = setInterval(fetchLocations, 1000); // 1-second refresh for high-speed simulation
        return () => clearInterval(interval);
    }, []);

    // Poll vehicle list for pairing status
    useEffect(() => {
        const fetchVehicles = async () => {
            try {
                const resp = await fetch(`${API_URL}/vehicles`, { headers: authHeaders() });
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
        <div className="auth-page" style={{ height: '100vh', display: 'flex' }}>
            <Sidebar />

            <main style={{ flex: 1, overflowY: 'auto', padding: '40px', background: 'rgba(2, 6, 23, 0.4)' }}>
                {/* Dashboard Header */}
                <header style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '40px' }}>
                    <div>
                        <h1 style={{ fontSize: '32px', fontWeight: '800', marginBottom: '8px' }}>V2X Infrastructure Command</h1>
                        <p style={{ color: 'var(--text-secondary)' }}>Industry-grade autonomous fleet control and AI risk monitoring</p>
                    </div>
                    <div style={{ display: 'flex', gap: '24px', alignItems: 'center' }}>
                        <div className="glass" style={{ padding: '12px 20px', display: 'flex', alignItems: 'center', gap: '12px' }}>
                            <div className={`ws-dot ${wsConnected ? '' : 'disconnected'}`} style={{ width: '10px', height: '10px', borderRadius: '50%', background: wsConnected ? 'var(--accent-cyan)' : '#ef4444' }} />
                            <span style={{ fontSize: '14px', fontWeight: '700' }}>{wsConnected ? 'LIVE FEED ACTIVE' : 'NETWORK STANDBY'}</span>
                        </div>
                        <div className="glass" style={{ padding: '12px 20px' }}>
                            <span style={{ fontSize: '12px', color: 'var(--text-secondary)', marginRight: '8px' }}>UPTIME</span>
                            <span style={{ fontSize: '14px', fontWeight: '800', fontFamily: 'monospace' }}>{uptimeStr}</span>
                        </div>
                    </div>
                </header>

                {/* Dashboard Grid */}
                <div style={{ display: 'grid', gridTemplateColumns: '2fr 1.2fr', gap: '32px' }}>

                    {/* Primary Area: Map */}
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '32px' }}>
                        <div className="glass" style={{ height: '550px', padding: '24px', position: 'relative' }}>
                            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '20px' }}>
                                <h3 style={{ fontSize: '18px', fontWeight: '800' }}>Real-time Fleet Visualizer</h3>
                                <div style={{ display: 'flex', gap: '12px' }}>
                                    <span style={{ padding: '4px 12px', background: 'rgba(34, 211, 238, 0.1)', color: 'var(--accent-cyan)', borderRadius: '20px', fontSize: '11px', fontWeight: '800' }}>50+ NODES</span>
                                    <span style={{ padding: '4px 12px', background: 'rgba(59, 130, 246, 0.1)', color: 'var(--accent-blue)', borderRadius: '20px', fontSize: '11px', fontWeight: '800' }}>AI TRAJECTORY</span>
                                </div>
                            </div>
                            <div style={{ height: '450px', borderRadius: '16px', overflow: 'hidden' }}>
                                <VehicleMap vehicles={vehicleLocations} />
                            </div>
                        </div>

                        {/* Stats Row */}
                        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '32px' }}>
                            <div className="glass" style={{ padding: '24px' }}>
                                <h4 style={{ color: 'var(--text-secondary)', fontSize: '12px', marginBottom: '12px', textTransform: 'uppercase' }}>Connected Vehicles</h4>
                                <div style={{ fontSize: '32px', fontWeight: '800', color: 'var(--accent-cyan)' }}>
                                    <AnimatedCounter value={vehicleLocations.length} />
                                </div>
                            </div>
                            <div className="glass" style={{ padding: '24px' }}>
                                <h4 style={{ color: 'var(--text-secondary)', fontSize: '12px', marginBottom: '12px', textTransform: 'uppercase' }}>Risk Detections</h4>
                                <div style={{ fontSize: '32px', fontWeight: '800', color: '#fca5a5' }}>
                                    <AnimatedCounter value={alerts.length} />
                                </div>
                            </div>
                            <div className="glass" style={{ padding: '24px' }}>
                                <h4 style={{ color: 'var(--text-secondary)', fontSize: '12px', marginBottom: '12px', textTransform: 'uppercase' }}>Network Ping</h4>
                                <div style={{ fontSize: '32px', fontWeight: '800', color: 'var(--accent-blue)' }}>
                                    {latencyData[latencyData.length - 1]?.toFixed(0) || 0}<span style={{ fontSize: '16px', marginLeft: '4px' }}>ms</span>
                                </div>
                            </div>
                        </div>

                        {/* Analytics Panel */}
                        <div className="glass" style={{ padding: '24px' }}>
                            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '20px' }}>
                                <h3 style={{ fontSize: '18px', fontWeight: '800' }}>AI Collision Prediction Stream</h3>
                                <span style={{ color: 'var(--text-secondary)', fontSize: '12px' }}>Real-time Thread Latency</span>
                            </div>
                            <LatencyGraph latencyData={latencyData} />
                        </div>
                    </div>

                    {/* Secondary Area: Controls & Alerts */}
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '32px' }}>

                        {/* Simulation Control */}
                        <SimulationPanel />

                        {/* Collision Feed */}
                        <div className="glass" style={{ padding: '24px', flex: 1, maxHeight: '420px', display: 'flex', flexDirection: 'column' }}>
                            <h3 style={{ fontSize: '18px', fontWeight: '800', marginBottom: '20px' }}>🚨 Live Threat Feed</h3>
                            <div style={{ overflowY: 'auto', flex: 1 }}>
                                <AlertPanel alerts={alerts} />
                            </div>
                        </div>

                        {/* Pairing Card */}
                        <div className="glass" style={{ padding: '24px' }}>
                            <h3 style={{ fontSize: '18px', fontWeight: '800', marginBottom: '20px' }}>Device Provisioning</h3>
                            <PairingStatus vehicles={vehicles} />
                            <div style={{ marginTop: '24px', padding: '20px', background: 'rgba(255,255,255,0.02)', borderRadius: '16px', border: '1px solid var(--glass-border)' }}>
                                <p style={{ fontSize: '13px', fontWeight: '600', marginBottom: '12px', color: 'var(--text-secondary)' }}>Provision New Hardware Node</p>
                                <div style={{ display: 'flex', gap: '10px' }}>
                                    <input
                                        type="text"
                                        id="new-v-name-v3"
                                        placeholder="Node UID (e.g. OBU-771)"
                                        style={{ flex: 1, padding: '12px', background: 'rgba(0,0,0,0.2)', border: '1px solid var(--glass-border)', color: 'white', borderRadius: '8px', fontSize: '14px' }}
                                    />
                                    <button
                                        className="auth-btn"
                                        style={{ width: 'auto', padding: '0 20px', height: '46px' }}
                                        onClick={async () => {
                                            const name = document.getElementById('new-v-name-v3').value;
                                            if (!name) return;
                                            try {
                                                const resp = await fetch(`${API_URL}/vehicles`, {
                                                    method: 'POST',
                                                    headers: { ...authHeaders(), 'Content-Type': 'application/json' },
                                                    body: JSON.stringify({ name })
                                                });
                                                if (resp.ok) window.location.reload();
                                            } catch (err) { alert('Failed to provision'); }
                                        }}
                                    >Add</button>
                                </div>
                            </div>
                        </div>

                        {/* Health Panel */}
                        <div className="glass" style={{ padding: '24px' }}>
                            <HealthPanel health={health} vehicleCount={vehicleLocations.length} />
                        </div>

                    </div>
                </div>
            </main>
        </div>
    );
}

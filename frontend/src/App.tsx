import { useState, useEffect, useCallback, useRef } from 'react';
import { useNetworkWS } from './hooks/useNetworkWS';
import TopologyView from './components/TopologyView';
import RCAPanel from './components/RCAPanel';
import AlertsPanel from './components/AlertsPanel';
import ArchComparison from './components/ArchComparison';
import ExperimentPanel from './components/ExperimentPanel';
import RecommendationPanel from './components/RecommendationPanel';
import type { PredictionResult, TimelineEntry } from './types';

type LeftTab  = 'rca' | 'alerts' | 'fingerprint';
type RightTab = 'arch' | 'experiment' | 'recommend';

export default function App() {
  const { snapshot, rca, alerts, connected, triggerSurge } = useNetworkWS();
  const [leftTab,  setLeftTab]  = useState<LeftTab>('rca');
  const [rightTab, setRightTab] = useState<RightTab>('arch');
  const [showHeatmap, setShowHeatmap] = useState(false);
  const [prediction, setPrediction]   = useState<PredictionResult | null>(null);
  const [timeline, setTimeline]       = useState<TimelineEntry[]>([]);
  const [replaySnap, setReplaySnap]   = useState<typeof snapshot>(null);
  const [isReplaying, setIsReplaying] = useState(false);
  const [fingerprint, setFingerprint] = useState<{current:string; anomaly:{anomaly:boolean;avg_similarity:number}; evolution:{mutation_rate:number;unique_states:number;stability:number}} | null>(null);
  const sliderRef = useRef<HTMLInputElement>(null);
  const displaySnap = isReplaying ? replaySnap : snapshot;

  // Fetch prediction periodically
  useEffect(() => {
    const load = async () => {
      try {
        const r = await fetch('/api/predict');
        if (r.ok) setPrediction(await r.json());
      } catch {/* ignore */}
    };
    load();
    const i = setInterval(load, 5000);
    return () => clearInterval(i);
  }, []);

  // Fetch timeline periodically
  useEffect(() => {
    const load = async () => {
      try {
        const r = await fetch('/api/timeline?limit=200');
        if (r.ok) setTimeline(await r.json());
      } catch {/* ignore */}
    };
    load();
    const i = setInterval(load, 8000);
    return () => clearInterval(i);
  }, []);

  // Fetch fingerprint when tab active
  useEffect(() => {
    if (leftTab !== 'fingerprint') return;
    const load = async () => {
      try {
        const r = await fetch('/api/fingerprint');
        if (r.ok) setFingerprint(await r.json());
      } catch {/* ignore */}
    };
    load();
    const i = setInterval(load, 3000);
    return () => clearInterval(i);
  }, [leftTab]);

  const sliderValue = displaySnap
    ? Math.max(0, timeline.findIndex(t => t.tick >= (displaySnap?.tick ?? 0)))
    : 0;

  const handleSliderChange = useCallback(async (e: React.ChangeEvent<HTMLInputElement>) => {
    const idx = parseInt(e.target.value);
    const entry = timeline[idx];
    if (!entry) return;
    setIsReplaying(true);
    try {
      const r = await fetch(`/api/replay/go/${entry.id}`);
      if (r.ok) setReplaySnap(await r.json());
    } catch {/* ignore */}
  }, [timeline]);

  const handleReplayBtn = useCallback(async (action: 'start' | 'end' | 'rewind' | 'forward') => {
    if (action === 'end') { setIsReplaying(false); setReplaySnap(null); return; }
    setIsReplaying(true);
    try {
      const url = action === 'start'   ? '/api/replay/start'
                : action === 'rewind'  ? '/api/replay/rewind?steps=5'
                : '/api/replay/forward?steps=5';
      const r = await fetch(url);
      if (r.ok) setReplaySnap(await r.json());
    } catch {/* ignore */}
  }, []);

  const handleSurge = useCallback(() => {
    triggerSurge(20);
  }, [triggerSurge]);

  const metrics = displaySnap?.metrics;
  const avgLoad = displaySnap
    ? displaySnap.nodes.reduce((s, n) => s + n.load, 0) / Math.max(displaySnap.nodes.length, 1)
    : 0;

  return (
    <div className="noc-root">
      {/* ── Header ─────────────────────────────────────────────────────────── */}
      <header className="noc-header">
        <div className="noc-header-title">
          <div className="noc-header-logo">TN</div>
          TEMPORAL NETWORK ANALYSIS PLATFORM
          {isReplaying && (
            <span style={{ color: 'var(--glow-amber)', fontSize: 10, marginLeft: 8 }}>
              ⏪ REPLAY MODE [t={displaySnap?.tick}]
            </span>
          )}
        </div>

        <div className="noc-header-kpis">
          <div className="kpi-item">
            <div className="kpi-label">Packet Rate</div>
            <div className="kpi-value kpi-cyan">
              {metrics?.packet_rate.toFixed(1) ?? '—'} <span style={{fontSize:9}}>pps</span>
            </div>
          </div>
          <div className="kpi-item">
            <div className="kpi-label">Avg Latency</div>
            <div className="kpi-value kpi-amber">
              {metrics?.avg_latency.toFixed(1) ?? '—'} <span style={{fontSize:9}}>ms</span>
            </div>
          </div>
          <div className="kpi-item">
            <div className="kpi-label">Avg Load</div>
            <div className={`kpi-value ${avgLoad > 0.8 ? 'kpi-red' : avgLoad > 0.5 ? 'kpi-amber' : 'kpi-green'}`}>
              {(avgLoad * 100).toFixed(0)}<span style={{fontSize:9}}>%</span>
            </div>
          </div>
          <div className="kpi-item">
            <div className="kpi-label">Nodes</div>
            <div className="kpi-value kpi-purple">
              {displaySnap?.nodes.length ?? '—'}
            </div>
          </div>
          <div className="kpi-item">
            <div className="kpi-label">Alerts</div>
            <div className={`kpi-value ${alerts.length > 0 ? 'kpi-red' : 'kpi-green'}`}>
              {alerts.length}
            </div>
          </div>
          {displaySnap?.surge_active && (
            <div className="kpi-item">
              <div className="kpi-label">Traffic</div>
              <div className="kpi-value kpi-red" style={{ animation: 'pulse 0.8s infinite' }}>⚡ SURGE</div>
            </div>
          )}
        </div>

        <div className="header-status">
          <div className={`status-dot ${connected ? (displaySnap?.live_capture ? 'live' : 'sim') : 'error'}`} />
          {connected
            ? (displaySnap?.live_capture ? 'LIVE CAPTURE' : 'SIM MODE')
            : 'CONNECTING…'}
          <span style={{ color: 'var(--text-dim)', marginLeft: 6, fontFamily: 'var(--font-mono)', fontSize: 10 }}>
            T={displaySnap?.tick ?? 0}
          </span>
        </div>
      </header>

      {/* ── Body ───────────────────────────────────────────────────────────── */}
      <div className="noc-body">

        {/* ── Left Panel ─────────────────────────────────────────────────── */}
        <div className="panel">
          <div className="panel-header">
            <span>●</span> Analysis Console
          </div>
          <div className="panel-tab-bar">
            {(['rca', 'alerts', 'fingerprint'] as LeftTab[]).map(t => (
              <button
                key={t}
                className={`panel-tab ${leftTab === t ? 'active' : ''}`}
                onClick={() => setLeftTab(t)}
              >
                {t === 'rca' ? '🔍 RCA' : t === 'alerts' ? '🔔 Alerts' : '🧬 DNA'}
              </button>
            ))}
          </div>
          <div className="panel-content">
            {leftTab === 'rca' && <RCAPanel causes={rca} />}
            {leftTab === 'alerts' && <AlertsPanel alerts={alerts} />}
            {leftTab === 'fingerprint' && (
              <div>
                <div className="card">
                  <div className="card-title">🧬 Network DNA</div>
                  <div className="fingerprint-display">
                    {fingerprint?.current ?? (displaySnap?.fingerprint ?? '—')}
                  </div>
                  {fingerprint?.anomaly && (
                    <div style={{ marginTop: 6 }}>
                      <span className={`badge badge-${fingerprint.anomaly.anomaly ? 'critical' : 'low'}`}>
                        {fingerprint.anomaly.anomaly ? '⚠ ANOMALY' : '✓ NORMAL'}
                      </span>
                      <span style={{ marginLeft: 6, fontSize: 10, color: 'var(--text-dim)' }}>
                        sim={fingerprint.anomaly.avg_similarity.toFixed(3)}
                      </span>
                    </div>
                  )}
                </div>
                {fingerprint?.evolution && (
                  <div className="card">
                    <div className="card-title">📈 Evolution Metrics</div>
                    {[
                      { label: 'Stability',      val: fingerprint.evolution.stability, fmt: (v: number) => `${(v*100).toFixed(1)}%`, color: 'var(--glow-green)' },
                      { label: 'Mutation Rate',  val: fingerprint.evolution.mutation_rate, fmt: (v: number) => v.toFixed(3), color: 'var(--glow-amber)' },
                      { label: 'Unique States',  val: fingerprint.evolution.unique_states / Math.max(fingerprint.evolution.unique_states, 1), fmt: () => String(fingerprint.evolution.unique_states), color: 'var(--glow-purple)' },
                    ].map(m => (
                      <div className="metric-row" key={m.label}>
                        <div className="metric-label">{m.label}</div>
                        <div className="metric-bar-wrap">
                          <div className="metric-bar-fill" style={{ width: `${m.val * 100}%`, background: m.color }} />
                        </div>
                        <div className="metric-val" style={{ color: m.color }}>{m.fmt(m.val)}</div>
                      </div>
                    ))}
                  </div>
                )}
                {/* Prediction hotspots */}
                {prediction?.hotspots && prediction.hotspots.length > 0 && (
                  <div className="card">
                    <div className="card-title">🌡 Congestion Hotspots</div>
                    {prediction.hotspots.slice(0, 5).map(h => (
                      <div className="metric-row" key={h.node_id}>
                        <div className="metric-label">Node {h.node_id}</div>
                        <div className="metric-bar-wrap">
                          <div className="metric-bar-fill" style={{ width: `${h.probability * 100}%`, background: h.severity === 'critical' ? 'var(--glow-red)' : 'var(--glow-amber)' }} />
                        </div>
                        <div className="metric-val" style={{ color: h.severity === 'critical' ? 'var(--glow-red)' : 'var(--glow-amber)' }}>
                          {(h.probability * 100).toFixed(0)}%
                        </div>
                      </div>
                    ))}
                    <div style={{ marginTop: 6, display: 'flex', gap: 6, alignItems: 'center' }}>
                      <span style={{ fontSize: 9, color: 'var(--text-dim)' }}>Method:</span>
                      <span style={{ fontSize: 9, color: 'var(--glow-cyan)', fontFamily: 'var(--font-mono)' }}>
                        {prediction.method}
                      </span>
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>

        {/* ── Center: Topology + Timeline ──────────────────────────────────── */}
        <div className="center-area">
          <div className="panel-header" style={{ background: 'var(--bg-panel)', borderBottom: '1px solid var(--border)', borderRight: 'none', flexShrink: 0 }}>
            <span style={{ color: 'var(--glow-cyan)' }}>◈</span>
            Network Topology — Live State
            <div style={{ marginLeft: 'auto', display: 'flex', gap: 6 }}>
              <button
                className={`btn ${showHeatmap ? 'primary' : ''}`}
                style={{ padding: '3px 10px' }}
                onClick={() => setShowHeatmap(!showHeatmap)}
              >
                {showHeatmap ? '🌡 Heat ON' : '🌡 Heat OFF'}
              </button>
            </div>
          </div>

          <div className="topology-container">
            <TopologyView
              snapshot={displaySnap}
              prediction={prediction}
              showHeatmap={showHeatmap}
            />
          </div>

          {/* Node load mini-metrics */}
          {displaySnap && (
            <div style={{
              display: 'flex', gap: 6, padding: '6px 14px', overflowX: 'auto',
              background: 'var(--bg-panel)', borderTop: '1px solid var(--border)', flexShrink: 0,
            }}>
              {displaySnap.nodes.map(n => (
                <div key={n.id} style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 2, minWidth: 40 }}>
                  <div style={{
                    width: 24, height: 24,
                    borderRadius: '50%',
                    border: `2px solid ${n.load > 0.8 ? 'var(--glow-red)' : n.load > 0.5 ? 'var(--glow-amber)' : 'var(--glow-green)'}`,
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    fontSize: 7, fontFamily: 'var(--font-mono)', fontWeight: 700,
                    color: n.load > 0.8 ? 'var(--glow-red)' : n.load > 0.5 ? 'var(--glow-amber)' : 'var(--glow-green)',
                    background: `rgba(${n.load > 0.8 ? '255,59,92' : n.load > 0.5 ? '255,170,0' : '0,255,136'},0.1)`,
                  }}>
                    {Math.round(n.load * 100)}
                  </div>
                  <div style={{ fontSize: 7, color: 'var(--text-dim)', textAlign: 'center', lineHeight: 1 }}>{n.label}</div>
                </div>
              ))}
            </div>
          )}

          {/* Timeline */}
          <div className="timeline-bar">
            <span className="timeline-label">Timeline</span>
            <button className="timeline-btn" onClick={() => handleReplayBtn('start')} title="Go to start">⏮</button>
            <button className="timeline-btn" onClick={() => handleReplayBtn('rewind')} title="Rewind 5">◀◀</button>
            <input
              ref={sliderRef}
              type="range"
              className="timeline-slider"
              min={0}
              max={Math.max(timeline.length - 1, 1)}
              value={sliderValue}
              onChange={handleSliderChange}
            />
            <button className="timeline-btn" onClick={() => handleReplayBtn('forward')} title="Forward 5">▶▶</button>
            <button className="timeline-btn" onClick={() => handleReplayBtn('end')} title="Go live">⏭</button>
            <button className="timeline-btn surge" onClick={handleSurge} title="Inject Traffic Surge">⚡</button>
            <span className="timeline-tick">t={displaySnap?.tick ?? 0}</span>
            {timeline.length > 0 && (
              <span style={{ fontSize: 9, color: 'var(--text-dim)', fontFamily: 'var(--font-mono)' }}>
                {timeline.length} snaps
              </span>
            )}
          </div>
        </div>

        {/* ── Right Panel ─────────────────────────────────────────────────── */}
        <div className="panel">
          <div className="panel-header">
            <span>◉</span> Research Console
          </div>
          <div className="panel-tab-bar">
            {(['arch', 'experiment', 'recommend'] as RightTab[]).map(t => (
              <button
                key={t}
                className={`panel-tab ${rightTab === t ? 'active' : ''}`}
                onClick={() => setRightTab(t)}
              >
                {t === 'arch' ? '⚙ Sim' : t === 'experiment' ? '🧪 Exp' : '💡 Rec'}
              </button>
            ))}
          </div>
          <div className="panel-content">
            {rightTab === 'arch'       && <ArchComparison snapshot={displaySnap} />}
            {rightTab === 'experiment' && <ExperimentPanel snapshot={displaySnap} />}
            {rightTab === 'recommend'  && <RecommendationPanel snapshot={displaySnap} />}
          </div>
        </div>
      </div>
    </div>
  );
}

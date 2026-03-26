import { useState, useEffect, useCallback, useRef } from 'react';
import { Play, Square, Radio, Wifi, WifiOff, Zap, Activity, TrendingUp, Server } from 'lucide-react';
import NetworkGraph from './components/NetworkGraph';
import MetricsPanel from './components/MetricsPanel';

const API = 'http://localhost:8000';

function StatCard({ icon: Icon, label, value, unit, color, subtext }) {
  return (
    <div className="metric-card p-3 flex items-center gap-3">
      <div className="p-2 rounded-lg" style={{ background: `${color}22` }}>
        <Icon size={18} style={{ color }} />
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-xs text-slate-500 truncate">{label}</p>
        <p className="text-lg font-bold" style={{ color }}>
          {value ?? '—'}
          <span className="text-xs font-normal text-slate-500 ml-1">{unit}</span>
        </p>
        {subtext && <p className="text-xs text-slate-600 truncate">{subtext}</p>}
      </div>
    </div>
  );
}

export default function App() {
  const [data, setData] = useState(null);
  const [running, setRunning] = useState(false);
  const [liveCapture, setLiveCapture] = useState(false);
  const [error, setError] = useState('');
  const pollRef = useRef(null);

  const fetchData = useCallback(async () => {
    try {
      const res = await fetch(`${API}/data`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const json = await res.json();
      setData(json);
      setRunning(json.running);
      setLiveCapture(json.live_capture);
      setError('');
    } catch (e) {
      setError('Cannot reach backend at ' + API);
    }
  }, []);

  // Auto-poll every second
  useEffect(() => {
    fetchData();
    pollRef.current = setInterval(fetchData, 1000);
    return () => clearInterval(pollRef.current);
  }, [fetchData]);

  const handleStart = async () => {
    try {
      await fetch(`${API}/start_capture`, { method: 'POST' });
      setRunning(true);
      setError('');
    } catch {
      setError('Failed to start. Is the backend running?');
    }
  };

  const handleStop = async () => {
    try {
      await fetch(`${API}/stop_capture`, { method: 'POST' });
      setRunning(false);
    } catch {
      setError('Failed to stop.');
    }
  };

  const improvement = data?.improvement ?? 0;
  const improvColor = improvement > 0 ? '#10b981' : improvement < 0 ? '#ef4444' : '#94a3b8';

  return (
    <div className="h-screen w-screen flex flex-col overflow-hidden" style={{ background: '#050d1a' }}>
      {/* ── TOP BAR ── */}
      <header className="flex items-center justify-between px-5 py-3 border-b"
        style={{ borderColor: 'rgba(30,58,95,0.8)', background: 'rgba(5,13,26,0.95)', backdropFilter: 'blur(10px)', zIndex: 20 }}>
        <div className="flex items-center gap-3">
          <div className="p-1.5 rounded-lg" style={{ background: 'rgba(59,130,246,0.15)' }}>
            <Radio size={22} className="text-blue-400" />
          </div>
          <div>
            <h1 className="text-base font-bold text-white leading-tight">
              5G UPF Placement Dashboard
            </h1>
            <p className="text-xs text-slate-500">Real-Time Dynamic Optimization • Wireshark Live Traffic</p>
          </div>
        </div>

        {/* Status & Controls */}
        <div className="flex items-center gap-3">
          {error && (
            <span className="text-xs text-red-400 bg-red-900/20 border border-red-800 px-2 py-1 rounded">
              {error}
            </span>
          )}

          <div className="flex items-center gap-1.5 px-2 py-1 rounded-full text-xs"
            style={{ background: liveCapture ? 'rgba(16,185,129,0.1)' : 'rgba(148,163,184,0.1)', border: `1px solid ${liveCapture ? 'rgba(16,185,129,0.3)' : 'rgba(148,163,184,0.2)'}` }}>
            {liveCapture ? <Wifi size={12} className="text-emerald-400" /> : <WifiOff size={12} className="text-slate-500" />}
            <span className={liveCapture ? 'text-emerald-400' : 'text-slate-500'}>
              {liveCapture ? 'Live Capture' : 'Simulated'}
            </span>
          </div>

          {running && (
            <div className="flex items-center gap-1.5 text-xs text-emerald-400">
              <span className="w-2 h-2 rounded-full bg-emerald-400 status-live inline-block" />
              LIVE
            </div>
          )}

          <button
            onClick={running ? handleStop : handleStart}
            className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-semibold transition-all duration-200"
            style={{
              background: running
                ? 'linear-gradient(135deg, #7f1d1d, #991b1b)'
                : 'linear-gradient(135deg, #1d4ed8, #2563eb)',
              color: 'white',
              boxShadow: running
                ? '0 0 20px rgba(239,68,68,0.3)'
                : '0 0 20px rgba(59,130,246,0.3)',
            }}>
            {running ? <><Square size={14} /> Stop</> : <><Play size={14} /> Start</>}
          </button>
        </div>
      </header>

      {/* ── MAIN LAYOUT ── */}
      <div className="flex flex-1 overflow-hidden gap-0">

        {/* LEFT: Stat cards + Network Graph */}
        <div className="flex flex-col flex-1 min-w-0 overflow-hidden p-4 gap-3">
          {/* Stat cards row */}
          <div className="grid grid-cols-4 gap-3 flex-shrink-0">
            <StatCard icon={Activity} label="Packet Rate" color="#fbbf24"
              value={data?.packet_rate?.toFixed(1)} unit="pkt/s"
              subtext={`Avg size: ${data?.avg_pkt_size?.toFixed(0) ?? '—'} B`} />
            <StatCard icon={Zap} label="Latency (Dynamic)" color="#3b82f6"
              value={data?.latency?.toFixed(2)} unit="ms"
              subtext={`Static: ${data?.latency_static?.toFixed(2) ?? '—'} ms`} />
            <StatCard icon={Server} label="UPF Node" color="#ef4444"
              value={`Node ${data?.upf_node ?? '—'}`} unit=""
              subtext={`Traffic load: ${data?.traffic_load?.toFixed(2) ?? '—'}`} />
            <StatCard icon={TrendingUp} label="Improvement" color={improvColor}
              value={improvement > 0 ? `+${improvement}` : improvement} unit="%"
              subtext="Dynamic vs Static" />
          </div>

          {/* Network Graph */}
          <div className="flex-1 min-h-0 rounded-xl overflow-hidden border"
            style={{ borderColor: 'rgba(30,58,95,0.6)' }}>
            <NetworkGraph data={data} running={running} />
          </div>
        </div>

        {/* RIGHT: Metrics Panel */}
        <div className="w-80 flex-shrink-0 p-4 pl-0 overflow-hidden">
          <MetricsPanel data={data} />
        </div>
      </div>

      {/* ── FOOTER ── */}
      <footer className="flex items-center justify-between px-5 py-1.5 border-t text-xs text-slate-600"
        style={{ borderColor: 'rgba(30,58,95,0.5)', background: 'rgba(5,13,26,0.95)' }}>
        <span>Timestamp: {data?.timestamp ?? 0}s</span>
        <span>5G Core Network • UPF Dynamic Placement Simulation</span>
        <span>Energy (dyn): <span className="text-slate-400">{data?.energy?.toFixed(2) ?? '—'}</span></span>
      </footer>
    </div>
  );
}

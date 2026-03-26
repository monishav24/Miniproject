import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, Legend, AreaChart, Area
} from 'recharts';

const CustomTooltip = ({ active, payload, label }) => {
  if (active && payload && payload.length) {
    return (
      <div className="bg-slate-900 border border-slate-700 rounded-lg p-2 text-xs">
        <p className="text-slate-400 mb-1">t = {label}s</p>
        {payload.map(p => (
          <p key={p.name} style={{ color: p.color }}>
            {p.name}: <span className="font-bold">{Number(p.value).toFixed(2)}</span>
          </p>
        ))}
      </div>
    );
  }
  return null;
};

function ChartCard({ title, children, accent }) {
  return (
    <div className="metric-card p-4 flex flex-col gap-2">
      <div className="flex items-center gap-2">
        <div className="w-1 h-5 rounded-full" style={{ background: accent }} />
        <h3 className="text-sm font-semibold text-slate-300">{title}</h3>
      </div>
      {children}
    </div>
  );
}

export default function MetricsPanel({ data }) {
  const latency = data?.history?.latency || [];
  const energy = data?.history?.energy || [];
  const pktRate = data?.history?.packet_rate || [];
  const improvement = data?.history?.improvement || [];

  return (
    <div className="flex flex-col gap-3 h-full overflow-y-auto pr-1">
      {/* Latency Chart */}
      <ChartCard title="Latency (ms) — Dynamic vs Static" accent="#3b82f6">
        <ResponsiveContainer width="100%" height={140}>
          <AreaChart data={latency} margin={{ top: 5, right: 10, left: -20, bottom: 0 }}>
            <defs>
              <linearGradient id="gradDynLat" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3} />
                <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
              </linearGradient>
              <linearGradient id="gradStatLat" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#f87171" stopOpacity={0.3} />
                <stop offset="95%" stopColor="#f87171" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
            <XAxis dataKey="t" tick={{ fontSize: 10, fill: '#64748b' }} />
            <YAxis tick={{ fontSize: 10, fill: '#64748b' }} />
            <Tooltip content={<CustomTooltip />} />
            <Legend wrapperStyle={{ fontSize: '11px', paddingTop: '4px' }} />
            <Area type="monotone" dataKey="dynamic" stroke="#3b82f6" fill="url(#gradDynLat)"
              dot={false} strokeWidth={2} name="Dynamic UPF" />
            <Area type="monotone" dataKey="static" stroke="#f87171" fill="url(#gradStatLat)"
              dot={false} strokeWidth={2} name="Static UPF" strokeDasharray="5 3" />
          </AreaChart>
        </ResponsiveContainer>
      </ChartCard>

      {/* Energy Chart */}
      <ChartCard title="Energy Cost — Dynamic vs Static" accent="#8b5cf6">
        <ResponsiveContainer width="100%" height={130}>
          <LineChart data={energy} margin={{ top: 5, right: 10, left: -20, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
            <XAxis dataKey="t" tick={{ fontSize: 10, fill: '#64748b' }} />
            <YAxis tick={{ fontSize: 10, fill: '#64748b' }} />
            <Tooltip content={<CustomTooltip />} />
            <Legend wrapperStyle={{ fontSize: '11px', paddingTop: '4px' }} />
            <Line type="monotone" dataKey="dynamic" stroke="#8b5cf6" dot={false}
              strokeWidth={2} name="Dynamic" />
            <Line type="monotone" dataKey="static" stroke="#f59e0b" dot={false}
              strokeWidth={2} strokeDasharray="5 3" name="Static" />
          </LineChart>
        </ResponsiveContainer>
      </ChartCard>

      {/* Packet Rate */}
      <ChartCard title="Packet Rate (pkt/s) — Live Traffic" accent="#fbbf24">
        <ResponsiveContainer width="100%" height={120}>
          <AreaChart data={pktRate} margin={{ top: 5, right: 10, left: -20, bottom: 0 }}>
            <defs>
              <linearGradient id="gradPkt" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#fbbf24" stopOpacity={0.4} />
                <stop offset="95%" stopColor="#fbbf24" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
            <XAxis dataKey="t" tick={{ fontSize: 10, fill: '#64748b' }} />
            <YAxis tick={{ fontSize: 10, fill: '#64748b' }} />
            <Tooltip content={<CustomTooltip />} />
            <Area type="monotone" dataKey="value" stroke="#fbbf24" fill="url(#gradPkt)"
              dot={false} strokeWidth={2} name="Pkt/s" />
          </AreaChart>
        </ResponsiveContainer>
      </ChartCard>

      {/* Improvement */}
      <ChartCard title="Latency Improvement % (Dynamic vs Static)" accent="#10b981">
        <ResponsiveContainer width="100%" height={110}>
          <AreaChart data={improvement} margin={{ top: 5, right: 10, left: -20, bottom: 0 }}>
            <defs>
              <linearGradient id="gradImp" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#10b981" stopOpacity={0.4} />
                <stop offset="95%" stopColor="#10b981" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
            <XAxis dataKey="t" tick={{ fontSize: 10, fill: '#64748b' }} />
            <YAxis tick={{ fontSize: 10, fill: '#64748b' }} unit="%" />
            <Tooltip content={<CustomTooltip />} />
            <Area type="monotone" dataKey="value" stroke="#10b981" fill="url(#gradImp)"
              dot={false} strokeWidth={2} name="Improvement" />
          </AreaChart>
        </ResponsiveContainer>
      </ChartCard>
    </div>
  );
}

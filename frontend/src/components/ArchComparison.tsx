import { useState, useCallback } from 'react';
import type { Alternative } from '../types';

interface Props {
  snapshot: { tick: number } | null;
}

export default function ArchComparison({ snapshot }: Props) {
  const [alts, setAlts] = useState<Alternative[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError]     = useState('');

  const run = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const res = await fetch('/api/simulate/alternatives');
      if (!res.ok) throw new Error(await res.text());
      const data = await res.json();
      setAlts(data.alternatives || []);
    } catch (e: unknown) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  }, []);

  return (
    <div>
      <div style={{ marginBottom: 8, display: 'flex', gap: 6 }}>
        <button className="btn primary" onClick={run} disabled={loading || !snapshot}>
          {loading ? <><span className="spinner" /> Running…</> : '▶ Run Simulation'}
        </button>
      </div>

      {error && (
        <div style={{ color: 'var(--glow-red)', fontSize: 10, marginBottom: 8 }}>{error}</div>
      )}

      {alts.length > 0 && (
        <>
          <div style={{ marginBottom: 8 }}>
            <div className="heatmap-legend">
              <span>Rank→Performance:</span>
              <div className="heatmap-gradient" />
              <span>Worst</span>
            </div>
          </div>

          <table className="compare-table">
            <thead>
              <tr>
                <th>#</th>
                <th>Strategy</th>
                <th>Latency</th>
                <th>Tput</th>
                <th>Drop%</th>
              </tr>
            </thead>
            <tbody>
              {alts.map((alt) => (
                <tr key={alt.rank} className={alt.rank === 1 ? 'rank-1' : ''}>
                  <td style={{ color: alt.rank === 1 ? 'var(--glow-green)' : 'var(--text-dim)' }}>
                    {alt.rank === 1 ? '★' : alt.rank}
                  </td>
                  <td style={{ maxWidth: 130, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {alt.label}
                  </td>
                  <td style={{ color: alt.rank === 1 ? 'var(--glow-cyan)' : undefined }}>
                    {alt.metrics.avg_latency_ms.toFixed(1)}ms
                  </td>
                  <td>{alt.metrics.throughput_mbps.toFixed(0)}</td>
                  <td style={{ color: alt.metrics.packet_drop_rate > 0.05 ? 'var(--glow-red)' : undefined }}>
                    {(alt.metrics.packet_drop_rate * 100).toFixed(1)}%
                  </td>
                </tr>
              ))}
            </tbody>
          </table>

          {alts[0] && (
            <div className="card" style={{ marginTop: 10 }}>
              <div className="card-title">★ Best: {alts[0].label}</div>
              <div style={{ fontSize: 11, color: 'var(--text-secondary)' }}>
                Avg latency {alts[0].metrics.avg_latency_ms.toFixed(1)}ms ·
                Throughput {alts[0].metrics.throughput_mbps.toFixed(0)} Mbps ·
                Congestion {(alts[0].metrics.congestion_score * 100).toFixed(0)}%
              </div>
            </div>
          )}
        </>
      )}

      {!loading && !alts.length && !error && (
        <div className="empty-state">
          <span>Click "Run Simulation" to compare architectures</span>
        </div>
      )}
    </div>
  );
}

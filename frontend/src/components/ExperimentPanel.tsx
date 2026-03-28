import { useState, useCallback } from 'react';
import type { ExperimentResult } from '../types';

interface Props {
  snapshot: { tick: number } | null;
}

export default function ExperimentPanel({ snapshot }: Props) {
  const [results, setResults] = useState<ExperimentResult[]>([]);
  const [summary, setSummary] = useState<Record<string, unknown> | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError]     = useState('');
  const [expId, setExpId]     = useState('');

  const run = useCallback(async () => {
    setLoading(true);
    setError('');
    setResults([]);
    setSummary(null);
    try {
      const res = await fetch('/api/experiment/run', { method: 'POST' });
      if (!res.ok) throw new Error(await res.text());
      const data = await res.json();
      setResults(data.results || []);
      setSummary(data.summary || null);
      setExpId(data.experiment_id || '');
    } catch (e: unknown) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  }, []);

  return (
    <div>
      <div style={{ marginBottom: 8, display: 'flex', gap: 6, alignItems: 'center' }}>
        <button className="btn primary" onClick={run} disabled={loading || !snapshot}>
          {loading
            ? <><span className="spinner" /> Running 6 experiments…</>
            : '▶ Run Experiment Suite'}
        </button>
        {expId && (
          <span style={{ fontFamily: 'var(--font-mono)', fontSize: 9, color: 'var(--text-dim)' }}>
            #{expId}
          </span>
        )}
      </div>

      {error && (
        <div style={{ color: 'var(--glow-red)', fontSize: 10, marginBottom: 8 }}>{error}</div>
      )}

      {summary && (
        <div className="card" style={{ marginBottom: 10 }}>
          <div className="card-title">📊 Suite Summary</div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 4 }}>
            <div>
              <div style={{ fontSize: 9, color: 'var(--text-dim)' }}>BEST EXPERIMENT</div>
              <div style={{ fontSize: 11, color: 'var(--glow-green)', fontWeight: 600 }}>
                {String(summary.best_experiment)}
              </div>
            </div>
            <div>
              <div style={{ fontSize: 9, color: 'var(--text-dim)' }}>BEST LATENCY</div>
              <div style={{ fontSize: 11, color: 'var(--glow-cyan)', fontFamily: 'var(--font-mono)' }}>
                {Number(summary.best_latency_ms).toFixed(1)}ms
              </div>
            </div>
            <div>
              <div style={{ fontSize: 9, color: 'var(--text-dim)' }}>BEST STRATEGY</div>
              <div style={{ fontSize: 11, color: 'var(--text-primary)' }}>
                {String(summary.best_strategy)}
              </div>
            </div>
            <div>
              <div style={{ fontSize: 9, color: 'var(--text-dim)' }}>WORST CASE</div>
              <div style={{ fontSize: 11, color: 'var(--glow-amber)' }}>
                {String(summary.worst_experiment)}
              </div>
            </div>
          </div>
        </div>
      )}

      {results.length > 0 && results.map((r) => (
        <div key={r.rank} className="exp-row">
          <span className="exp-rank">
            {r.rank === 1 ? '★' : r.rank}
          </span>
          <div>
            <div className="exp-name">{r.experiment}</div>
            <div style={{ fontSize: 9, color: 'var(--text-dim)' }}>
              {r.surge_injected && <span style={{ color: 'var(--glow-red)' }}>⚡SURGE · </span>}
              {r.best_strategy} · {r.duration_s}s
            </div>
          </div>
          <div className="exp-latency">{r.best_metrics.avg_latency_ms?.toFixed(1)}ms</div>
        </div>
      ))}

      {!loading && !results.length && !error && (
        <div className="empty-state">
          <span>Click "Run Experiment Suite" to test all configurations</span>
        </div>
      )}
    </div>
  );
}

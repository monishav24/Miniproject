import { useState, useCallback } from 'react';
import type { Recommendation } from '../types';

interface Props {
  snapshot: { tick: number } | null;
}

const priorityColor: Record<string, string> = {
  critical: 'var(--glow-red)',
  high:     'var(--glow-amber)',
  medium:   'var(--glow-purple)',
  low:      'var(--glow-green)',
};

export default function RecommendationPanel({ snapshot }: Props) {
  const [recs, setRecs]   = useState<Recommendation[]>([]);
  const [loading, setLoading] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch('/api/recommend');
      const data = await res.json();
      setRecs(data.recommendations || []);
    } catch {/* ignore */}
    setLoading(false);
  }, []);

  return (
    <div>
      <div style={{ marginBottom: 8 }}>
        <button className="btn" onClick={load} disabled={loading || !snapshot}>
          {loading ? <><span className="spinner" /> Loading…</> : '🔄 Refresh'}
        </button>
      </div>

      {recs.length === 0 && !loading && (
        <div className="empty-state">
          <span>Click Refresh to get recommendations</span>
        </div>
      )}

      {recs.map((r) => (
        <div key={r.id} className="card" style={{ borderLeft: `3px solid ${priorityColor[r.priority] || 'var(--border)'}` }}>
          <div className="card-title">
            <span style={{ color: priorityColor[r.priority] || 'var(--text-secondary)' }}>
              {r.priority === 'critical' ? '🔴' : r.priority === 'high' ? '🟠' : '🟡'}
            </span>
            {r.title}
          </div>

          <div className="confidence-bar" style={{ marginBottom: 5 }}>
            <div
              className="confidence-fill"
              style={{ width: `${r.confidence * 100}%`, background: priorityColor[r.priority] || 'var(--glow-cyan)' }}
            />
          </div>
          <div style={{ fontSize: 9, color: 'var(--text-dim)', fontFamily: 'var(--font-mono)', marginBottom: 4 }}>
            confidence {Math.round(r.confidence * 100)}%
          </div>

          <div className="cause-desc" style={{ marginBottom: 4 }}>{r.description}</div>
          <div style={{ fontSize: 11, color: 'var(--glow-cyan)', fontWeight: 600 }}>
            Expected: {r.expected_improvement}
          </div>
        </div>
      ))}
    </div>
  );
}

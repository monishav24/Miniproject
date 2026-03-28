import type { RCACause } from '../types';

interface Props {
  causes: RCACause[];
}

const severityColor: Record<string, string> = {
  critical: 'var(--glow-red)',
  high:     'var(--glow-amber)',
  medium:   'var(--glow-purple)',
  low:      'var(--glow-green)',
};

export default function RCAPanel({ causes }: Props) {
  if (!causes.length) {
    return (
      <div className="empty-state">
        <div className="spinner" />
        <span>Analyzing network…</span>
      </div>
    );
  }

  return (
    <div>
      {causes.map((c, i) => (
        <div key={i} className="cause-row">
          <div className="cause-header">
            <span className="cause-name">{c.cause}</span>
            <span className={`badge badge-${c.severity}`}>{c.severity}</span>
          </div>
          <div className="confidence-bar">
            <div
              className="confidence-fill"
              style={{
                width: `${c.confidence * 100}%`,
                background: severityColor[c.severity] || 'var(--glow-cyan)',
              }}
            />
          </div>
          <span style={{ fontSize: 9, color: 'var(--text-dim)', fontFamily: 'var(--font-mono)' }}>
            confidence {Math.round(c.confidence * 100)}%
          </span>
          <div className="cause-desc">{c.description}</div>
          {c.recommendation && (
            <div className="rec-text">→ {c.recommendation}</div>
          )}
        </div>
      ))}
    </div>
  );
}

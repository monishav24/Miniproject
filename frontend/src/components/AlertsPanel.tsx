import type { Alert } from '../types';

interface Props { alerts: Alert[] }

const icons: Record<string, string> = {
  critical: '🔴',
  high:     '🟠',
  medium:   '🟡',
  low:      '🟢',
};

export default function AlertsPanel({ alerts }: Props) {
  if (!alerts.length) {
    return (
      <div className="empty-state">
        <span style={{ fontSize: 18 }}>✅</span>
        <span>No active alerts</span>
      </div>
    );
  }

  return (
    <div>
      {alerts.map((a, i) => (
        <div key={i} className={`alert-row ${a.severity}`}>
          <span className="alert-icon">{icons[a.severity] ?? '⚪'}</span>
          <div className="alert-content">
            <div className="alert-title">{a.type}</div>
            <div className="alert-desc">{a.description}</div>
            <div className="alert-tick">t={a.tick} · {Math.round(a.confidence * 100)}% confidence</div>
          </div>
        </div>
      ))}
    </div>
  );
}

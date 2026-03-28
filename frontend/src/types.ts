// Shared TypeScript types for the NOC dashboard

export interface NetworkNode {
  id: number;
  label: string;
  type: 'gNB' | 'MEC' | 'Core' | 'Transit';
  pos: [number, number];
  load: number;
  load_history: number[];
}

export interface NetworkEdge {
  source: number;
  target: number;
  latency: number;
  bandwidth: number;
  utilization: number;
  packet_drops: number;
  util_history: number[];
}

export interface NetworkMetrics {
  packet_rate: number;
  avg_latency: number;
  packet_rate_hist: number[];
  latency_hist: number[];
  timestamps: number[];
}

export interface NetworkSnapshot {
  tick: number;
  timestamp: number;
  live_capture: boolean;
  surge_active: boolean;
  nodes: NetworkNode[];
  edges: NetworkEdge[];
  metrics: NetworkMetrics;
  fingerprint: string;
}

export interface RCACause {
  cause: string;
  confidence: number;
  severity: 'critical' | 'high' | 'medium' | 'low';
  affected_nodes?: number[];
  affected_edges?: [number, number][];
  description: string;
  recommendation: string;
}

export interface Alert {
  tick: number;
  timestamp: number;
  type: string;
  severity: string;
  confidence: number;
  description: string;
}

export interface AltMetrics {
  avg_latency_ms: number;
  throughput_mbps: number;
  packet_drop_rate: number;
  congestion_score: number;
  energy_cost: number;
  avg_utilization: number;
}

export interface Alternative {
  rank: number;
  label: string;
  strategy: string;
  capacity_boost: number;
  extra_node: boolean;
  metrics: AltMetrics;
  score: number;
}

export interface Recommendation {
  id: string;
  title: string;
  confidence: number;
  priority: string;
  description: string;
  expected_improvement: string;
  action: string;
}

export interface ExperimentResult {
  rank: number;
  experiment: string;
  surge_injected: boolean;
  capacity_boost: number;
  duration_s: number;
  best_strategy: string;
  best_metrics: AltMetrics;
  recommendation: Record<string, unknown>;
}

export interface PredictionResult {
  node_congestion_probability: Record<string, number>;
  node_forecasts: Record<string, number[]>;
  edge_congestion_probability: Record<string, number>;
  horizon_ticks: number;
  method: string;
  hotspots: { node_id: number; probability: number; severity: string }[];
}

export interface TimelineEntry {
  id: number;
  timestamp: number;
  tick: number;
  label: string;
  fingerprint: string;
  surge: number;
  tag: string;
}

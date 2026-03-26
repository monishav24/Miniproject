import { useCallback, useRef, useEffect } from 'react';
import ForceGraph2D from 'react-force-graph-2d';

const NODE_COLORS = {
  gNB: '#3b82f6',   // blue
  MEC: '#6366f1',   // indigo
  Core: '#8b5cf6',  // purple
};
const UPF_COLOR = '#ef4444';     // red
const TRAFFIC_COLOR = '#fbbf24'; // yellow

export default function NetworkGraph({ data, running }) {
  const fgRef = useRef();

  useEffect(() => {
    if (fgRef.current) {
      fgRef.current.d3Force('charge').strength(-240);
      fgRef.current.d3Force('link').distance(80);
    }
  }, []);

  const graphData = {
    nodes: (data?.nodes || []).map(n => ({
      id: n.id,
      type: n.type,
      load: n.load,
      isUPF: n.id === data?.upf_node,
    })),
    links: (data?.edges || []).map(e => ({
      source: e.source,
      target: e.target,
      latency: e.latency,
      energy: e.energy,
    })),
  };

  const paintNode = useCallback((node, ctx, globalScale) => {
    const isUPF = node.isUPF;
    const color = isUPF ? UPF_COLOR : (NODE_COLORS[node.type] || '#60a5fa');
    const size = isUPF ? 12 : 8;

    // Glow
    if (isUPF) {
      ctx.beginPath();
      ctx.arc(node.x, node.y, size + 6, 0, 2 * Math.PI);
      ctx.fillStyle = 'rgba(239,68,68,0.25)';
      ctx.fill();
    } else if (node.load > 5) {
      ctx.beginPath();
      ctx.arc(node.x, node.y, size + 4, 0, 2 * Math.PI);
      ctx.fillStyle = `rgba(251,191,36,${node.load / 20})`;
      ctx.fill();
    }

    // Node circle
    ctx.beginPath();
    ctx.arc(node.x, node.y, size, 0, 2 * Math.PI);
    ctx.fillStyle = color;
    ctx.fill();
    ctx.strokeStyle = isUPF ? '#fca5a5' : 'rgba(255,255,255,0.2)';
    ctx.lineWidth = isUPF ? 2.5 : 1;
    ctx.stroke();

    // Label
    const label = isUPF ? `UPF (${node.type}${node.id})` : `${node.type}${node.id}`;
    const fontSize = Math.max(5, 11 / globalScale);
    ctx.font = `${isUPF ? 'bold ' : ''}${fontSize}px Inter, sans-serif`;
    ctx.textAlign = 'center';
    ctx.textBaseline = 'top';
    ctx.fillStyle = isUPF ? '#fca5a5' : 'rgba(226,232,240,0.8)';
    ctx.fillText(label, node.x, node.y + size + 2);
  }, []);

  const linkColor = useCallback((link) => {
    const load = data?.traffic_load || 0;
    if (load > 6) return `rgba(251,191,36,${0.4 + load / 20})`;
    return 'rgba(99,102,241,0.4)';
  }, [data?.traffic_load]);

  const linkWidth = useCallback((link) => {
    return 1 + (data?.traffic_load || 0) * 0.08;
  }, [data?.traffic_load]);

  return (
    <div className="relative w-full h-full rounded-xl overflow-hidden"
      style={{ background: 'linear-gradient(135deg, #05111e 0%, #060d1c 100%)' }}>
      {/* Legend */}
      <div className="absolute top-3 right-3 z-10 flex flex-col gap-1">
        {[
          { color: '#3b82f6', label: 'gNB (Base Station)' },
          { color: '#6366f1', label: 'MEC Node' },
          { color: '#8b5cf6', label: 'Core Node' },
          { color: '#ef4444', label: 'UPF (Active)' },
          { color: '#fbbf24', label: 'Traffic Load' },
        ].map(({ color, label }) => (
          <div key={label} className="flex items-center gap-1.5 text-xs text-slate-400">
            <div className="w-2.5 h-2.5 rounded-full" style={{ background: color }} />
            <span>{label}</span>
          </div>
        ))}
      </div>

      {!running && (
        <div className="absolute inset-0 flex items-center justify-center z-10">
          <p className="text-slate-500 text-lg font-medium">Press Start to begin simulation</p>
        </div>
      )}

      <ForceGraph2D
        ref={fgRef}
        graphData={graphData}
        nodeCanvasObject={paintNode}
        nodeCanvasObjectMode={() => 'replace'}
        linkColor={linkColor}
        linkWidth={linkWidth}
        backgroundColor="transparent"
        width={undefined}
        height={undefined}
        cooldownTicks={100}
        onEngineStop={() => fgRef.current?.zoomToFit(400, 40)}
      />
    </div>
  );
}

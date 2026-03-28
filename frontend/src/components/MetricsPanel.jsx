import { useRef, useEffect } from 'react';
import * as d3 from 'd3';

/**
 * MetricsPanel — SVG-based chart panel.
 * Drop-in replacement for the old recharts-based component.
 * Props: { data }
 *   data.history.latency      = [{ t, dynamic, static }]
 *   data.history.energy       = [{ t, dynamic, static }]
 *   data.history.packet_rate  = [{ t, value }]
 *   data.history.improvement  = [{ t, value }]
 */
export default function MetricsPanel({ data }) {
  const latency    = data?.history?.latency     || [];
  const energy     = data?.history?.energy      || [];
  const pktRate    = data?.history?.packet_rate || [];
  const improvement = data?.history?.improvement || [];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 12, height: '100%', overflowY: 'auto', paddingRight: 4 }}>
      <ChartCard title="Latency (ms) — Dynamic vs Static" accent="#3b82f6">
        <AreaLineChart
          data={latency}
          series={[
            { key: 'dynamic', color: '#3b82f6', label: 'Dynamic UPF' },
            { key: 'static',  color: '#f87171', label: 'Static UPF', dashed: true },
          ]}
          height={140}
          xKey="t"
        />
      </ChartCard>

      <ChartCard title="Energy Cost — Dynamic vs Static" accent="#8b5cf6">
        <AreaLineChart
          data={energy}
          series={[
            { key: 'dynamic', color: '#8b5cf6', label: 'Dynamic' },
            { key: 'static',  color: '#f59e0b', label: 'Static', dashed: true },
          ]}
          height={130}
          xKey="t"
          area={false}
        />
      </ChartCard>

      <ChartCard title="Packet Rate (pkt/s) — Live Traffic" accent="#fbbf24">
        <AreaLineChart
          data={pktRate}
          series={[{ key: 'value', color: '#fbbf24', label: 'Pkt/s' }]}
          height={120}
          xKey="t"
        />
      </ChartCard>

      <ChartCard title="Latency Improvement % (Dynamic vs Static)" accent="#10b981">
        <AreaLineChart
          data={improvement}
          series={[{ key: 'value', color: '#10b981', label: 'Improvement' }]}
          height={110}
          xKey="t"
          unit="%"
        />
      </ChartCard>
    </div>
  );
}

/* ── Shared card wrapper ──────────────────────────────────────────────── */
function ChartCard({ title, children, accent }) {
  return (
    <div style={{
      background: 'rgba(15,23,42,0.7)',
      border: '1px solid rgba(255,255,255,0.06)',
      borderRadius: 10,
      padding: '12px 14px',
      display: 'flex', flexDirection: 'column', gap: 8,
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        <div style={{ width: 3, height: 20, borderRadius: 2, background: accent, flexShrink: 0 }} />
        <span style={{ fontSize: 13, fontWeight: 600, color: '#cbd5e1' }}>{title}</span>
      </div>
      {children}
    </div>
  );
}

/* ── D3 SVG Chart ────────────────────────────────────────────────────── */
function AreaLineChart({ data, series, height, xKey, unit = '', area = true }) {
  const ref = useRef(null);

  useEffect(() => {
    if (!ref.current || !data.length) return;
    const el  = ref.current;
    const W   = el.clientWidth || 300;
    const H   = height;
    const margin = { top: 8, right: 12, left: 28, bottom: 20 };
    const iW  = W - margin.left - margin.right;
    const iH  = H - margin.top  - margin.bottom;

    d3.select(el).selectAll('*').remove();

    const svg = d3.select(el).append('svg')
      .attr('width', W).attr('height', H);

    const g = svg.append('g')
      .attr('transform', `translate(${margin.left},${margin.top})`);

    // Scales
    const xVals = data.map(d => d[xKey]);
    const x = d3.scaleLinear().domain(d3.extent(xVals)).range([0, iW]);

    const allYVals = series.flatMap(s => data.map(d => d[s.key] ?? 0));
    const [yMin, yMax] = d3.extent(allYVals);
    const y = d3.scaleLinear()
      .domain([Math.min(0, yMin ?? 0), (yMax ?? 1) * 1.15])
      .range([iH, 0]);

    // Grid
    g.append('g')
      .call(d3.axisLeft(y).ticks(4).tickFormat(v => `${v}${unit}`))
      .call(ax => ax.select('.domain').remove())
      .call(ax => ax.selectAll('.tick line')
        .attr('stroke', 'rgba(255,255,255,0.05)')
        .attr('x2', iW))
      .call(ax => ax.selectAll('text')
        .attr('fill', '#475569').attr('font-size', 9));

    g.append('g')
      .attr('transform', `translate(0,${iH})`)
      .call(d3.axisBottom(x).ticks(5))
      .call(ax => ax.select('.domain').remove())
      .call(ax => ax.selectAll('.tick line').remove())
      .call(ax => ax.selectAll('text')
        .attr('fill', '#475569').attr('font-size', 9));

    // Defs for area gradients
    const defs = svg.append('defs');

    series.forEach(s => {
      const gradId = `grad-${s.key}-${Math.random().toString(36).slice(2,6)}`;
      const grad = defs.append('linearGradient')
        .attr('id', gradId).attr('x1','0').attr('y1','0').attr('x2','0').attr('y2','1');
      grad.append('stop').attr('offset','5%').attr('stop-color', s.color).attr('stop-opacity', 0.35);
      grad.append('stop').attr('offset','95%').attr('stop-color', s.color).attr('stop-opacity', 0);
      s._gradId = gradId;
    });

    // Area + line per series
    series.forEach(s => {
      const lineGen = d3.line()
        .x(d => x(d[xKey]))
        .y(d => y(d[s.key] ?? 0))
        .curve(d3.curveMonotoneX);

      if (area) {
        const areaGen = d3.area()
          .x(d => x(d[xKey]))
          .y0(iH)
          .y1(d => y(d[s.key] ?? 0))
          .curve(d3.curveMonotoneX);

        g.append('path')
          .datum(data)
          .attr('fill', `url(#${s._gradId})`)
          .attr('d', areaGen);
      }

      g.append('path')
        .datum(data)
        .attr('fill', 'none')
        .attr('stroke', s.color)
        .attr('stroke-width', 2)
        .attr('stroke-dasharray', s.dashed ? '5,3' : null)
        .attr('d', lineGen);
    });

    // Mini legend
    const leg = g.append('g').attr('transform', `translate(${iW - 10}, 2)`);
    series.forEach((s, i) => {
      const lg = leg.append('g').attr('transform', `translate(0, ${i * 14})`);
      lg.append('line').attr('x1',-30).attr('x2',-18).attr('y1',5).attr('y2',5)
        .attr('stroke', s.color).attr('stroke-width', 2)
        .attr('stroke-dasharray', s.dashed ? '4,2' : null);
      lg.append('text').attr('x', -15).attr('y', 9)
        .attr('fill', '#64748b').attr('font-size', 9)
        .text(s.label);
    });

  }, [data, series, height, xKey, unit, area]);

  return <div ref={ref} style={{ width: '100%', height }} />;
}

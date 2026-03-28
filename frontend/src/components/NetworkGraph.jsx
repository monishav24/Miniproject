import { useEffect, useRef } from 'react';
import * as d3 from 'd3';

const NODE_COLORS = {
  gNB:  '#3b82f6',
  MEC:  '#6366f1',
  Core: '#8b5cf6',
};
const UPF_COLOR     = '#ef4444';
const TRAFFIC_COLOR = '#fbbf24';

/**
 * NetworkGraph — D3-based force-directed graph.
 * Drop-in replacement for the old react-force-graph-2d component.
 * Props: { data, running }
 *   data.nodes  = [{ id, type, load, isUPF? }]
 *   data.edges  = [{ source, target, latency, energy }]
 *   data.upf_node = number
 *   data.traffic_load = number
 */
export default function NetworkGraph({ data, running }) {
  const svgRef   = useRef(null);
  const simRef   = useRef(null);

  useEffect(() => {
    if (!svgRef.current) return;
    const el  = svgRef.current;
    const W   = el.clientWidth  || 600;
    const H   = el.clientHeight || 400;

    // Clear previous render
    d3.select(el).selectAll('*').remove();

    const svg = d3.select(el)
      .append('svg')
      .attr('width', W)
      .attr('height', H)
      .style('background', 'linear-gradient(135deg,#05111e 0%,#060d1c 100%)')
      .style('border-radius', '12px');

    if (!data || !running) {
      svg.append('text')
        .attr('x', W / 2).attr('y', H / 2)
        .attr('text-anchor', 'middle')
        .attr('fill', '#475569')
        .attr('font-size', 16)
        .text('Press Start to begin simulation');
      return;
    }

    const nodes = (data.nodes || []).map(n => ({
      ...n,
      isUPF: n.id === data.upf_node,
    }));
    const links = (data.edges || []).map(e => ({ ...e }));

    // Legend
    const legendData = [
      { color: '#3b82f6', label: 'gNB (Base Station)' },
      { color: '#6366f1', label: 'MEC Node' },
      { color: '#8b5cf6', label: 'Core Node' },
      { color: '#ef4444', label: 'UPF (Active)' },
      { color: '#fbbf24', label: 'Traffic Load' },
    ];
    const legend = svg.append('g').attr('transform', 'translate(12, 12)');
    legendData.forEach((d, i) => {
      const g = legend.append('g').attr('transform', `translate(0, ${i * 18})`);
      g.append('circle').attr('r', 5).attr('cx', 5).attr('cy', 5)
        .attr('fill', d.color);
      g.append('text').attr('x', 14).attr('y', 9)
        .attr('fill', '#94a3b8').attr('font-size', 11)
        .text(d.label);
    });

    // D3 force simulation
    const tload = data.traffic_load || 0;
    const linkColor = tload > 6
      ? `rgba(251,191,36,${Math.min(0.9, 0.4 + tload / 20)})`
      : 'rgba(99,102,241,0.4)';
    const linkW = 1 + tload * 0.08;

    const simulation = d3.forceSimulation(nodes)
      .force('link', d3.forceLink(links).id(d => d.id).distance(80))
      .force('charge', d3.forceManyBody().strength(-240))
      .force('center', d3.forceCenter(W / 2, H / 2));

    simRef.current = simulation;

    const link = svg.append('g')
      .selectAll('line')
      .data(links)
      .enter().append('line')
      .attr('stroke', linkColor)
      .attr('stroke-width', linkW);

    const node = svg.append('g')
      .selectAll('g')
      .data(nodes)
      .enter().append('g')
      .call(d3.drag()
        .on('start', (event, d) => {
          if (!event.active) simulation.alphaTarget(0.3).restart();
          d.fx = d.x; d.fy = d.y;
        })
        .on('drag', (event, d) => { d.fx = event.x; d.fy = event.y; })
        .on('end', (event, d) => {
          if (!event.active) simulation.alphaTarget(0);
          d.fx = null; d.fy = null;
        })
      );

    // Glow ring for UPF
    node.filter(d => d.isUPF)
      .append('circle')
      .attr('r', 18)
      .attr('fill', 'rgba(239,68,68,0.25)');

    // High-load glow
    node.filter(d => !d.isUPF && d.load > 5)
      .append('circle')
      .attr('r', 14)
      .attr('fill', d => `rgba(251,191,36,${d.load / 20})`);

    node.append('circle')
      .attr('r', d => d.isUPF ? 12 : 8)
      .attr('fill', d => d.isUPF ? UPF_COLOR : (NODE_COLORS[d.type] || '#60a5fa'))
      .attr('stroke', d => d.isUPF ? '#fca5a5' : 'rgba(255,255,255,0.2)')
      .attr('stroke-width', d => d.isUPF ? 2.5 : 1);

    node.append('text')
      .attr('text-anchor', 'middle')
      .attr('dy', d => (d.isUPF ? 12 : 8) + 12)
      .attr('fill', d => d.isUPF ? '#fca5a5' : 'rgba(226,232,240,0.8)')
      .attr('font-size', 10)
      .attr('font-weight', d => d.isUPF ? 'bold' : 'normal')
      .text(d => d.isUPF ? `UPF(${d.type}${d.id})` : `${d.type}${d.id}`);

    simulation.on('tick', () => {
      link
        .attr('x1', d => d.source.x).attr('y1', d => d.source.y)
        .attr('x2', d => d.target.x).attr('y2', d => d.target.y);
      node.attr('transform', d => `translate(${d.x},${d.y})`);
    });

    return () => simulation.stop();
  }, [data, running]);

  return <div ref={svgRef} style={{ width: '100%', height: '100%', borderRadius: 12 }} />;
}

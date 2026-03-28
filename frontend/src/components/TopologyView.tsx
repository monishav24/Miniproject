import { useEffect, useRef, useCallback } from 'react';
import * as d3 from 'd3';
import type { NetworkSnapshot, PredictionResult } from '../types';

interface Props {
  snapshot: NetworkSnapshot | null;
  prediction: PredictionResult | null;
  showHeatmap: boolean;
}

// Node type → color
const NODE_COLORS: Record<string, string> = {
  gNB:     '#3b9eff',
  MEC:     '#00ff88',
  Core:    '#ffaa00',
  Transit: '#9b59ff',
};

function loadColor(load: number, congProb?: number): string {
  const p = congProb ?? load;
  if (p >= 0.85) return '#ff3b5c';
  if (p >= 0.65) return '#ffaa00';
  if (p >= 0.4)  return '#ffdd57';
  return '#00ff88';
}

function edgeColor(utilization: number, drops: number): string {
  if (drops > 0.1 || utilization > 0.85) return '#ff3b5c';
  if (utilization > 0.65) return '#ffaa00';
  if (utilization > 0.4)  return '#3b9eff';
  return '#1e4080';
}

export default function TopologyView({ snapshot, prediction, showHeatmap }: Props) {
  const svgRef = useRef<SVGSVGElement>(null);
  const initialized = useRef(false);

  const getNodeProb = useCallback((id: number): number | undefined => {
    if (!prediction || !showHeatmap) return undefined;
    return prediction.node_congestion_probability[String(id)];
  }, [prediction, showHeatmap]);

  useEffect(() => {
    if (!svgRef.current || !snapshot) return;
    const svg = d3.select(svgRef.current);
    const { width, height } = svgRef.current.getBoundingClientRect();
    if (width === 0 || height === 0) return;

    // Project node positions from logical [-5,5] space to SVG coords
    const xScale = d3.scaleLinear().domain([-5, 5]).range([80, width - 80]);
    const yScale = d3.scaleLinear().domain([-3, 3.5]).range([height - 60, 60]);

    const nodeMap = new Map(snapshot.nodes.map(n => [n.id, n]));

    const getX = (id: number) => xScale((nodeMap.get(id)?.pos[0] ?? 0));
    const getY = (id: number) => yScale((nodeMap.get(id)?.pos[1] ?? 0));

    if (!initialized.current) {
      svg.selectAll('*').remove();

      // Defs: glow filters, arrow marker
      const defs = svg.append('defs');

      // Glow filter
      const filter = defs.append('filter').attr('id', 'glow').attr('x', '-50%').attr('y', '-50%').attr('width', '200%').attr('height', '200%');
      filter.append('feGaussianBlur').attr('stdDeviation', '3').attr('result', 'coloredBlur');
      const merge = filter.append('feMerge');
      merge.append('feMergeNode').attr('in', 'coloredBlur');
      merge.append('feMergeNode').attr('in', 'SourceGraphic');

      // Grid lines
      const gridG = svg.append('g').attr('class', 'grid');
      for (let i = 0; i <= 10; i++) {
        const x = (width / 10) * i;
        gridG.append('line').attr('x1', x).attr('y1', 0).attr('x2', x).attr('y2', height)
          .attr('stroke', 'rgba(30,64,128,0.3)').attr('stroke-width', 1);
      }
      for (let i = 0; i <= 8; i++) {
        const y = (height / 8) * i;
        gridG.append('line').attr('x1', 0).attr('y1', y).attr('x2', width).attr('y2', y)
          .attr('stroke', 'rgba(30,64,128,0.3)').attr('stroke-width', 1);
      }

      svg.append('g').attr('class', 'edges-group');
      svg.append('g').attr('class', 'nodes-group');
      svg.append('g').attr('class', 'labels-group');
      svg.append('g').attr('class', 'packets-group');

      initialized.current = true;
    }

    // ── Edges ──────────────────────────────────────────────────────────────────
    const edgesG = svg.select<SVGGElement>('.edges-group');
    const edgeSel = edgesG.selectAll<SVGLineElement, typeof snapshot.edges[0]>('line.edge')
      .data(snapshot.edges, (d) => `${d.source}-${d.target}`);

    edgeSel.enter()
      .append('line')
      .attr('class', 'edge')
      .attr('stroke-linecap', 'round')
      .merge(edgeSel)
      .attr('x1', d => getX(d.source))
      .attr('y1', d => getY(d.source))
      .attr('x2', d => getX(d.target))
      .attr('y2', d => getY(d.target))
      .attr('stroke-width', d => 1.5 + d.utilization * 3)
      .attr('stroke', d => edgeColor(d.utilization, d.packet_drops))
      .attr('opacity', d => 0.4 + d.utilization * 0.6);

    edgeSel.exit().remove();

    // ── Nodes ──────────────────────────────────────────────────────────────────
    const nodesG = svg.select<SVGGElement>('.nodes-group');
    const nodeSel = nodesG.selectAll<SVGGElement, typeof snapshot.nodes[0]>('g.node-g')
      .data(snapshot.nodes, d => String(d.id));

    const nodeEnter = nodeSel.enter()
      .append('g')
      .attr('class', 'node-g');

    // Outer glow ring
    nodeEnter.append('circle').attr('class', 'node-ring');
    // Main node circle
    nodeEnter.append('circle').attr('class', 'node-circle').attr('filter', 'url(#glow)');
    // Load indicator arc (outer ring)
    nodeEnter.append('circle').attr('class', 'node-load-ring');

    const nodeAll = nodeEnter.merge(nodeSel);

    nodeAll.attr('transform', d => `translate(${getX(d.id)}, ${getY(d.id)})`);

    nodeAll.select<SVGCircleElement>('circle.node-ring')
      .attr('r', d => 20 + d.load * 6)
      .attr('fill', 'none')
      .attr('stroke', d => {
        const prob = getNodeProb(d.id);
        return showHeatmap && prob !== undefined ? loadColor(d.load, prob)
          : NODE_COLORS[d.type] || '#3b9eff';
      })
      .attr('stroke-width', 1)
      .attr('opacity', 0.25);

    nodeAll.select<SVGCircleElement>('circle.node-circle')
      .attr('r', 14)
      .attr('fill', d => {
        const prob = getNodeProb(d.id);
        const base = NODE_COLORS[d.type] || '#3b9eff';
        if (showHeatmap && prob !== undefined) {
          // Blend base with heatmap color
          return loadColor(d.load, prob);
        }
        return base;
      })
      .attr('stroke', d => NODE_COLORS[d.type] || '#3b9eff')
      .attr('stroke-width', d.load > 0.8 ? 2.5 : 1.5)
      .attr('opacity', d => 0.8 + d.load * 0.2);

    nodeSel.exit().remove();

    // ── Labels ─────────────────────────────────────────────────────────────────
    const labelsG = svg.select<SVGGElement>('.labels-group');
    const labelSel = labelsG.selectAll<SVGGElement, typeof snapshot.nodes[0]>('g.label-g')
      .data(snapshot.nodes, d => String(d.id));

    const labelEnter = labelSel.enter().append('g').attr('class', 'label-g');
    labelEnter.append('text').attr('class', 'node-label-name');
    labelEnter.append('text').attr('class', 'node-label-load');

    const labelAll = labelEnter.merge(labelSel);
    labelAll.attr('transform', d => `translate(${getX(d.id)}, ${getY(d.id)})`);

    labelAll.select<SVGTextElement>('text.node-label-name')
      .attr('text-anchor', 'middle')
      .attr('dy', 26)
      .attr('font-family', 'Roboto Mono, monospace')
      .attr('font-size', 9)
      .attr('font-weight', '600')
      .attr('fill', '#7db0d0')
      .text(d => d.label);

    labelAll.select<SVGTextElement>('text.node-label-load')
      .attr('text-anchor', 'middle')
      .attr('dy', -18)
      .attr('font-family', 'Roboto Mono, monospace')
      .attr('font-size', 8)
      .attr('fill', d => loadColor(d.load))
      .text(d => `${Math.round(d.load * 100)}%`);

    labelSel.exit().remove();

    // ── Animated packet dots ───────────────────────────────────────────────────
    if (snapshot.metrics.packet_rate > 1) {
      const packetsG = svg.select<SVGGElement>('.packets-group');
      const randomEdge = snapshot.edges[Math.floor(Math.random() * snapshot.edges.length)];
      if (randomEdge) {
        const dot = packetsG.append('circle')
          .attr('r', 3)
          .attr('fill', snapshot.surge_active ? '#ff3b5c' : '#00d4ff')
          .attr('opacity', 0.9)
          .attr('cx', getX(randomEdge.source))
          .attr('cy', getY(randomEdge.source));

        dot.transition().duration(800).ease(d3.easeLinear)
          .attr('cx', getX(randomEdge.target))
          .attr('cy', getY(randomEdge.target))
          .attr('opacity', 0)
          .remove();
      }
    }

  }, [snapshot, prediction, showHeatmap, getNodeProb]);

  return (
    <svg
      ref={svgRef}
      style={{ width: '100%', height: '100%', background: 'transparent' }}
    />
  );
}

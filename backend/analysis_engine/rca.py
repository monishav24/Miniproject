"""
Root Cause Analysis Engine — graph-based causal inference for network degradation
"""
import math
from typing import Any, Dict, List

import networkx as nx
import numpy as np


def analyze_root_causes(snapshot: dict) -> List[Dict]:
    """
    Given a network snapshot, identify root causes of degradation.
    Returns ranked list of causes with confidence and affected nodes.
    """
    nodes = snapshot.get("nodes", [])
    edges = snapshot.get("edges", [])
    metrics = snapshot.get("metrics", {})

    causes = []

    if not nodes or not edges:
        return causes

    # Build graph from snapshot
    G = nx.Graph()
    for n in nodes:
        G.add_node(n["id"], load=n["load"], label=n.get("label", str(n["id"])), ntype=n.get("type", ""))
    for e in edges:
        G.add_edge(e["source"], e["target"],
                   latency=e["latency"],
                   utilization=e["utilization"],
                   packet_drops=e.get("packet_drops", 0))

    avg_load = np.mean([n["load"] for n in nodes]) if nodes else 0.0

    # ── 1. Node Overload ──────────────────────────────────────────────────────
    overloaded = [n for n in nodes if n["load"] > 0.8]
    if overloaded:
        worst = max(overloaded, key=lambda x: x["load"])
        confidence = min(0.99, 0.5 + worst["load"] * 0.5)
        causes.append({
            "cause":          "Node Overload",
            "confidence":     round(confidence, 3),
            "severity":       "critical" if worst["load"] > 0.9 else "high",
            "affected_nodes": [n["id"] for n in overloaded],
            "description":    f"Node {worst['label']} at {worst['load']*100:.1f}% capacity. "
                              f"{len(overloaded)} node(s) overloaded.",
            "recommendation": "Consider load shedding or spinning up additional MEC/Core nodes near the congested zone.",
        })

    # ── 2. Routing Bottleneck (betweenness centrality) ────────────────────────
    if len(G.nodes()) > 2:
        bc = nx.betweenness_centrality(G, weight="latency", normalized=True)
        max_node = max(bc, key=bc.get)
        max_bc   = bc[max_node]
        node_load = G.nodes[max_node].get("load", 0.0)
        if max_bc > 0.3 and node_load > 0.6:
            confidence = round(min(0.99, max_bc * 1.5 + node_load * 0.3), 3)
            causes.append({
                "cause":          "Routing Bottleneck",
                "confidence":     confidence,
                "severity":       "high",
                "affected_nodes": [max_node],
                "description":    f"Node {G.nodes[max_node].get('label', max_node)} is a routing bottleneck "
                                  f"(centrality={max_bc:.3f}, load={node_load:.2f}).",
                "recommendation": "Introduce alternative routing paths or deploy an additional transit node.",
            })

    # ── 3. Edge Congestion ────────────────────────────────────────────────────
    hot_edges = [e for e in edges if e["utilization"] > 0.75]
    if hot_edges:
        worst_edge = max(hot_edges, key=lambda x: x["utilization"])
        confidence = round(min(0.99, 0.4 + worst_edge["utilization"] * 0.6), 3)
        causes.append({
            "cause":          "Edge Congestion",
            "confidence":     confidence,
            "severity":       "high" if worst_edge["utilization"] > 0.9 else "medium",
            "affected_edges": [(e["source"], e["target"]) for e in hot_edges],
            "description":    f"Link {worst_edge['source']}–{worst_edge['target']} "
                              f"at {worst_edge['utilization']*100:.1f}% utilization. "
                              f"{len(hot_edges)} congested link(s).",
            "recommendation": "Increase link capacity or reroute traffic via load-balanced paths.",
        })

    # ── 4. Traffic Spike ──────────────────────────────────────────────────────
    pkt_hist = metrics.get("packet_rate_hist", [])
    if len(pkt_hist) >= 5:
        recent  = np.mean(pkt_hist[-3:])
        earlier = np.mean(pkt_hist[-10:-3]) if len(pkt_hist) >= 10 else np.mean(pkt_hist)
        if earlier > 0 and (recent - earlier) / earlier > 0.4:
            confidence = round(min(0.99, (recent - earlier) / (earlier + 0.001) * 0.5), 3)
            causes.append({
                "cause":          "Traffic Spike",
                "confidence":     confidence,
                "severity":       "medium",
                "affected_nodes": [],
                "description":    f"Packet rate jumped {((recent-earlier)/earlier*100):.0f}% "
                                  f"(from {earlier:.1f} to {recent:.1f} pps).",
                "recommendation": "Enable admission control or traffic shaping to smoothen spike bursts.",
            })

    # ── 5. Topology Imbalance ─────────────────────────────────────────────────
    if nodes:
        loads = [n["load"] for n in nodes]
        std   = float(np.std(loads))
        if std > 0.25 and avg_load > 0.3:
            imbalanced = [n for n in nodes if abs(n["load"] - avg_load) > std]
            confidence = round(min(0.9, std * 2), 3)
            causes.append({
                "cause":          "Topology Imbalance",
                "confidence":     confidence,
                "severity":       "medium",
                "affected_nodes": [n["id"] for n in imbalanced],
                "description":    f"Load distribution highly uneven (σ={std:.3f}, mean={avg_load:.3f}). "
                                  f"Some nodes idle while others overloaded.",
                "recommendation": "Redesign routing topology or apply traffic redistribution policies.",
            })

    # ── 6. Packet Loss ────────────────────────────────────────────────────────
    dropping = [e for e in edges if e.get("packet_drops", 0) > 0.05]
    if dropping:
        worst_drop = max(dropping, key=lambda x: x.get("packet_drops", 0))
        confidence = round(min(0.99, worst_drop["packet_drops"] * 10), 3)
        causes.append({
            "cause":          "Packet Loss Detected",
            "confidence":     confidence,
            "severity":       "critical" if worst_drop["packet_drops"] > 0.2 else "medium",
            "affected_edges": [(e["source"], e["target"]) for e in dropping],
            "description":    f"Link {worst_drop['source']}–{worst_drop['target']} "
                              f"dropping {worst_drop['packet_drops']*100:.1f}% of packets.",
            "recommendation": "Investigate link quality or reduce forwarded traffic load.",
        })

    # Sort by confidence descending
    causes.sort(key=lambda x: x["confidence"], reverse=True)
    return causes

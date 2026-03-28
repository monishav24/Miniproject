"""
Alternate Architecture Simulator — generates and evaluates alternative network designs
"""
import copy
import itertools
import random
import time
from typing import Dict, List

import networkx as nx
import numpy as np

from backend.collector.traffic_generator import NODE_META, EDGE_LIST, build_base_graph


ROUTING_STRATEGIES = ["shortest_path", "ospf_like", "load_balanced", "random_detour"]


def _build_graph_from_snapshot(snapshot: dict) -> nx.Graph:
    G = build_base_graph()
    if snapshot:
        for edge in snapshot.get("edges", []):
            u, v = edge["source"], edge["target"]
            if G.has_edge(u, v):
                G.edges[u, v]["latency"]     = edge["latency"]
                G.edges[u, v]["utilization"] = edge["utilization"]
                G.edges[u, v]["bandwidth"]   = edge["bandwidth"]
        for node in snapshot.get("nodes", []):
            if G.has_node(node["id"]):
                G.nodes[node["id"]]["load"] = node["load"]
    return G


def _evaluate_architecture(G: nx.Graph, strategy: str, extra_nodes: List[int] = None,
                             capacity_boost: float = 1.0) -> Dict:
    """Compute metrics for a given architecture + routing strategy."""
    total_latency   = 0.0
    total_drops     = 0.0
    total_util      = 0.0
    congested_edges = 0
    paths_computed  = 0

    gnb_nodes  = [n for n, d in G.nodes(data=True) if d.get("type") == "gNB"]
    core_nodes = [n for n, d in G.nodes(data=True) if d.get("type") in ("Core", "Transit")]

    for src in gnb_nodes:
        for dst in core_nodes:
            if src == dst:
                continue
            try:
                if strategy == "shortest_path":
                    path = nx.shortest_path(G, src, dst, weight="latency")
                elif strategy == "ospf_like":
                    # OSPF-like: uses inverse bandwidth as weight
                    for u, v in G.edges():
                        G.edges[u, v]["ospf_w"] = 1000.0 / max(G.edges[u, v]["bandwidth"] * capacity_boost, 1)
                    path = nx.shortest_path(G, src, dst, weight="ospf_w")
                elif strategy == "load_balanced":
                    # Prefer edges with lower utilization
                    for u, v in G.edges():
                        G.edges[u, v]["lb_w"] = G.edges[u, v]["latency"] + G.edges[u, v]["utilization"] * 20
                    path = nx.shortest_path(G, src, dst, weight="lb_w")
                else:  # random_detour
                    all_paths = list(nx.all_simple_paths(G, src, dst, cutoff=5))
                    path = random.choice(all_paths) if all_paths else [src, dst]
            except (nx.NetworkXNoPath, nx.NodeNotFound):
                total_latency += 999
                continue

            path_lat = 0.0
            path_drop = 0.0
            for i in range(len(path) - 1):
                if G.has_edge(path[i], path[i + 1]):
                    e = G.edges[path[i], path[i + 1]]
                    path_lat  += e["latency"]
                    path_drop += e.get("packet_drops", 0.0)
                    util = e["utilization"]
                    total_util += util
                    if util > 0.8:
                        congested_edges += 1
            total_latency += path_lat
            total_drops   += path_drop
            paths_computed += 1

    n = max(paths_computed, 1)
    avg_lat   = round(total_latency / n, 2)
    avg_drop  = round(total_drops   / n, 4)
    avg_util  = round(total_util    / max(paths_computed * 3, 1), 4)
    congestion_score = round(congested_edges / max(len(list(G.edges())), 1), 4)

    # Throughput proxy: inversely proportional to avg latency and congestion
    throughput = round(min(1000.0, 500.0 / max(avg_lat, 1) * (1 - congestion_score)), 2)

    # Energy proxy
    energy_cost = round(
        sum(G.edges[u, v]["utilization"] * G.edges[u, v].get("bandwidth", 100) * 0.001
            for u, v in G.edges()) + len(list(G.nodes())) * 0.5, 2
    )

    return {
        "avg_latency_ms":   avg_lat,
        "throughput_mbps":  throughput,
        "packet_drop_rate": avg_drop,
        "congestion_score": congestion_score,
        "energy_cost":      energy_cost,
        "avg_utilization":  avg_util,
        "paths_computed":   paths_computed,
    }


def simulate_alternatives(current_snapshot: dict) -> List[Dict]:
    """
    Generate and evaluate multiple alternative network architectures.
    Returns ranked list of alternatives.
    """
    G_base = _build_graph_from_snapshot(current_snapshot)
    alternatives = []

    configs = [
        {"strategy": "shortest_path",  "capacity_boost": 1.0, "add_node": False, "label": "Baseline (Shortest Path)"},
        {"strategy": "ospf_like",       "capacity_boost": 1.0, "add_node": False, "label": "OSPF-like Routing"},
        {"strategy": "load_balanced",   "capacity_boost": 1.0, "add_node": False, "label": "Load-Balanced Routing"},
        {"strategy": "shortest_path",   "capacity_boost": 2.0, "add_node": False, "label": "Capacity Doubled"},
        {"strategy": "load_balanced",   "capacity_boost": 1.5, "add_node": True,  "label": "Load-Balanced + Extra Node"},
        {"strategy": "ospf_like",       "capacity_boost": 1.5, "add_node": True,  "label": "OSPF + Capacity +50%"},
        {"strategy": "random_detour",   "capacity_boost": 1.0, "add_node": False, "label": "Random Detour (Worst)"},
    ]

    for cfg in configs:
        G = copy.deepcopy(G_base)

        # Apply capacity boost
        if cfg["capacity_boost"] != 1.0:
            for u, v in G.edges():
                G.edges[u, v]["bandwidth"] *= cfg["capacity_boost"]
                G.edges[u, v]["utilization"] /= cfg["capacity_boost"]

        # Add extra relay node
        extra_id = None
        if cfg["add_node"]:
            extra_id = max(G.nodes()) + 1
            G.add_node(extra_id, type="Transit", pos=[1.5, -3.0], label=f"Relay-X", load=0.1)
            # Connect to most-loaded Core nodes
            core_nodes = [n for n, d in G.nodes(data=True) if d.get("type") in ("Core", "Transit")]
            for cn in core_nodes[:2]:
                G.add_edge(extra_id, cn,
                           latency=random.uniform(1.5, 4.0),
                           bandwidth=500.0,
                           utilization=0.1,
                           packet_drops=0.0)
            gnb_nodes = [n for n, d in G.nodes(data=True) if d.get("type") == "gNB"]
            for gn in gnb_nodes[:2]:
                if not G.has_edge(extra_id, gn):
                    G.add_edge(extra_id, gn,
                               latency=random.uniform(2.0, 5.0),
                               bandwidth=300.0,
                               utilization=0.15,
                               packet_drops=0.0)

        metrics = _evaluate_architecture(G, cfg["strategy"], capacity_boost=cfg["capacity_boost"])

        alternatives.append({
            "label":          cfg["label"],
            "strategy":       cfg["strategy"],
            "capacity_boost": cfg["capacity_boost"],
            "extra_node":     extra_id is not None,
            "metrics":        metrics,
        })

    # Rank by composite score: lower latency + lower drop + lower congestion = better
    for alt in alternatives:
        m = alt["metrics"]
        alt["score"] = round(
            0.4 * (1 / max(m["avg_latency_ms"],   0.1)) +
            0.3 * m["throughput_mbps"] / 1000 +
            0.2 * (1 - m["congestion_score"]) +
            0.1 * (1 - m["packet_drop_rate"] * 100),
            5
        )

    alternatives.sort(key=lambda x: x["score"], reverse=True)
    for i, alt in enumerate(alternatives):
        alt["rank"] = i + 1

    return alternatives


def get_architecture_recommendation(alternatives: List[Dict]) -> Dict:
    if not alternatives:
        return {}
    best = alternatives[0]
    baseline = next((a for a in alternatives if "Baseline" in a["label"]), None)
    if baseline:
        lat_improvement = round(
            (baseline["metrics"]["avg_latency_ms"] - best["metrics"]["avg_latency_ms"])
            / max(baseline["metrics"]["avg_latency_ms"], 0.1) * 100, 1
        )
        tput_improvement = round(
            (best["metrics"]["throughput_mbps"] - baseline["metrics"]["throughput_mbps"])
            / max(baseline["metrics"]["throughput_mbps"], 0.1) * 100, 1
        )
    else:
        lat_improvement = tput_improvement = 0.0

    return {
        "recommended": best["label"],
        "strategy":    best["strategy"],
        "latency_improvement_pct":    lat_improvement,
        "throughput_improvement_pct": tput_improvement,
        "rationale": (
            f"'{best['label']}' scored highest across latency, throughput, "
            f"congestion, and energy metrics."
        ),
    }

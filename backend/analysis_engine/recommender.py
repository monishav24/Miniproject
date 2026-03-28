"""
Network Design Recommendation Engine
"""
from typing import Dict, List

import numpy as np


def generate_recommendations(snapshot: dict, rca_causes: List[Dict] = None,
                              alternatives: List[Dict] = None) -> List[Dict]:
    """
    Suggest improvements based on current network state and RCA results.
    Returns ranked list of recommendations with confidence scores.
    """
    nodes   = snapshot.get("nodes", [])
    edges   = snapshot.get("edges", [])
    metrics = snapshot.get("metrics", {})

    recommendations = []

    if not nodes:
        return recommendations

    loads = [n["load"] for n in nodes]
    avg_load = np.mean(loads) if loads else 0.0

    # ── Recommendation 1: Add Node Near Congestion ───────────────────────────
    overloaded = [n for n in nodes if n["load"] > 0.75]
    if overloaded:
        confidence = round(min(0.97, 0.5 + np.mean([n["load"] for n in overloaded]) * 0.5), 3)
        types      = set(n["type"] for n in overloaded)
        recommendations.append({
            "id":          "ADD_NODE",
            "title":       "Deploy Additional Node Near Congestion Zone",
            "confidence":  confidence,
            "priority":    "critical" if confidence > 0.85 else "high",
            "description": f"{len(overloaded)} node(s) ({', '.join(types)}) are overloaded. "
                           f"Adding relay/MEC capacity nearby will reduce their load.",
            "expected_improvement": f"~{round(confidence * 30, 0):.0f}% latency reduction",
            "action":      "add_node",
        })

    # ── Recommendation 2: Change Routing Strategy ────────────────────────────
    high_util_edges = [e for e in edges if e["utilization"] > 0.65]
    if len(high_util_edges) > len(edges) * 0.3:
        confidence = round(min(0.95, 0.4 + len(high_util_edges) / max(len(edges), 1)), 3)
        recommendations.append({
            "id":          "CHANGE_ROUTING",
            "title":       "Switch to Load-Balanced Routing",
            "confidence":  confidence,
            "priority":    "high",
            "description": f"{len(high_util_edges)}/{len(edges)} links are highly utilised. "
                           f"Load-balanced routing spreads traffic across underused paths.",
            "expected_improvement": f"~{round(confidence * 25, 0):.0f}% congestion reduction",
            "action":      "change_routing",
        })

    # ── Recommendation 3: Redistribute Load ──────────────────────────────────
    std = float(np.std(loads)) if loads else 0.0
    if std > 0.2 and avg_load > 0.3:
        idle = [n for n in nodes if n["load"] < 0.2]
        confidence = round(min(0.9, std * 3), 3)
        recommendations.append({
            "id":          "REDISTRIBUTE",
            "title":       "Redistribute Traffic Load",
            "confidence":  confidence,
            "priority":    "medium",
            "description": f"Load highly uneven (σ={std:.2f}). {len(idle)} node(s) are nearly idle "
                           f"while others are overloaded.",
            "expected_improvement": f"~{round(std * 50, 0):.0f}% load balance improvement",
            "action":      "redistribute",
        })

    # ── Recommendation 4: Increase Link Capacity ─────────────────────────────
    dropping_edges = [e for e in edges if e.get("packet_drops", 0) > 0.03]
    if dropping_edges:
        confidence = round(min(0.93, 0.5 + np.mean([e.get("packet_drops",0) for e in dropping_edges]) * 5), 3)
        recommendations.append({
            "id":          "UPGRADE_LINKS",
            "title":       "Upgrade High-Drop Links",
            "confidence":  confidence,
            "priority":    "high",
            "description": f"{len(dropping_edges)} link(s) dropping packets. "
                           f"Upgrading these links will improve reliability.",
            "expected_improvement": f"~{round(confidence * 20, 0):.0f}% packet delivery improvement",
            "action":      "upgrade_links",
        })

    # ── Recommendation 5: From Alternatives ──────────────────────────────────
    if alternatives and len(alternatives) > 1:
        best = alternatives[0]
        baseline = next((a for a in alternatives if "Baseline" in a["label"]), None)
        if baseline:
            lat_gain = baseline["metrics"]["avg_latency_ms"] - best["metrics"]["avg_latency_ms"]
            if lat_gain > 1.0:
                confidence = round(min(0.99, 0.5 + lat_gain / 20), 3)
                recommendations.append({
                    "id":          "ADOPT_BEST_ARCH",
                    "title":       f"Adopt '{best['label']}' Architecture",
                    "confidence":  confidence,
                    "priority":    "high",
                    "description": f"Simulation shows '{best['label']}' outperforms baseline by "
                                   f"{lat_gain:.1f}ms avg latency and higher throughput.",
                    "expected_improvement": f"~{round(lat_gain,1)}ms latency improvement",
                    "action":      "adopt_architecture",
                })

    # Sort by confidence
    recommendations.sort(key=lambda x: x["confidence"], reverse=True)
    return recommendations

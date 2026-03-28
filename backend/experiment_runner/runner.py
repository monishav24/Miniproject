"""
Autonomous Experiment Runner
Runs automated experiments testing multiple routing strategies and surge conditions.
"""
import time
import uuid
from typing import Any, Dict, List

from backend.simulation_engine.simulator import simulate_alternatives, get_architecture_recommendation
from backend.database.db import save_experiment


EXPERIMENT_CONFIGS = [
    {"name": "Baseline Analysis",       "surge": False, "capacity_boost": 1.0},
    {"name": "Traffic Surge Response",  "surge": True,  "capacity_boost": 1.0},
    {"name": "Capacity Upgrade",        "surge": False, "capacity_boost": 2.0},
    {"name": "Surge + Capacity",        "surge": True,  "capacity_boost": 2.0},
    {"name": "Minimal Resources",       "surge": False, "capacity_boost": 0.5},
    {"name": "Extreme Surge",           "surge": True,  "capacity_boost": 0.75},
]


def run_experiment_suite(current_snapshot: dict, custom_configs: List[Dict] = None) -> Dict:
    """
    Run full experiment suite:
    - For each config, simulate the network and evaluate all routing strategies
    - Return ranked results across all experiments
    """
    configs = custom_configs or EXPERIMENT_CONFIGS
    experiment_id = str(uuid.uuid4())[:8]
    all_results = []

    for cfg in configs:
        # Modify snapshot for surge
        snap = dict(current_snapshot)
        if cfg.get("surge"):
            snap = _inject_surge(snap)

        # Run alter architecture sim with capacity override
        start_ts = time.time()
        alternatives = simulate_alternatives(snap)

        # Apply capacity boost adjustment to labels
        if cfg.get("capacity_boost", 1.0) != 1.0:
            boost = cfg["capacity_boost"]
            for alt in alternatives:
                m = alt["metrics"]
                m["avg_latency_ms"]   = round(m["avg_latency_ms"]   / boost, 2)
                m["throughput_mbps"]  = round(m["throughput_mbps"]  * boost, 2)
                m["congestion_score"] = round(m["congestion_score"]  / boost, 4)

        elapsed = round(time.time() - start_ts, 3)
        best    = alternatives[0] if alternatives else {}
        rec     = get_architecture_recommendation(alternatives)

        all_results.append({
            "experiment":    cfg["name"],
            "surge_injected":cfg.get("surge", False),
            "capacity_boost":cfg.get("capacity_boost", 1.0),
            "duration_s":    elapsed,
            "best_strategy": best.get("label", "N/A"),
            "best_metrics":  best.get("metrics", {}),
            "recommendation":rec,
            "alternatives":  alternatives,
        })

    # Rank experiments by best achievable latency
    all_results.sort(key=lambda x: x["best_metrics"].get("avg_latency_ms", 999))
    for i, r in enumerate(all_results):
        r["rank"] = i + 1

    db_id = save_experiment(
        name=f"Suite-{experiment_id}",
        config={"configs": [c["name"] for c in configs]},
        results=all_results
    )

    return {
        "experiment_id": experiment_id,
        "db_id":         db_id,
        "total_configs": len(configs),
        "results":       all_results,
        "summary": {
            "best_experiment":   all_results[0]["experiment"] if all_results else "",
            "best_strategy":     all_results[0]["best_strategy"] if all_results else "",
            "best_latency_ms":   all_results[0]["best_metrics"].get("avg_latency_ms", 0) if all_results else 0,
            "worst_experiment":  all_results[-1]["experiment"] if all_results else "",
        },
    }


def _inject_surge(snapshot: dict) -> dict:
    """Simulate a traffic surge by scaling up utilization and load."""
    import copy
    import random
    s = copy.deepcopy(snapshot)
    for n in s.get("nodes", []):
        n["load"] = min(1.0, n["load"] * random.uniform(2.5, 3.5))
    for e in s.get("edges", []):
        e["utilization"]  = min(1.0, e["utilization"] * random.uniform(2.0, 4.0))
        e["latency"]      = e["latency"] * random.uniform(1.5, 2.5)
        e["packet_drops"] = min(0.5, e.get("packet_drops", 0) + random.uniform(0.05, 0.2))
    if "metrics" in s:
        pr = s["metrics"].get("packet_rate", 1.0)
        s["metrics"]["packet_rate"] = round(pr * 3.0, 2)
    return s

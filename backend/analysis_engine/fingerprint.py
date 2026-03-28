"""
Network DNA Fingerprinting — unique fingerprint per network state
"""
import hashlib
import json
import math
from typing import Dict, List, Tuple


def generate_fingerprint(snapshot: dict) -> str:
    """Generate a 16-char SHA-256-based fingerprint for a network snapshot."""
    nodes = snapshot.get("nodes", [])
    edges = snapshot.get("edges", [])
    data  = {
        "loads":     sorted([round(n["load"], 2) for n in nodes]),
        "latencies": sorted([round(e["latency"], 1) for e in edges]),
        "utils":     sorted([round(e["utilization"], 2) for e in edges]),
    }
    raw = json.dumps(data, sort_keys=True).encode()
    return hashlib.sha256(raw).hexdigest()[:16]


def fingerprint_similarity(fp_a: str, fp_b: str) -> float:
    """
    Compute Hamming-based similarity (0–1) between two fingerprints.
    """
    if fp_a == fp_b:
        return 1.0
    if len(fp_a) != len(fp_b):
        return 0.0
    matching = sum(c1 == c2 for c1, c2 in zip(fp_a, fp_b))
    return round(matching / len(fp_a), 4)


def fingerprint_evolution(fingerprints: List[str]) -> Dict:
    """
    Given a sequence of fingerprints over time, compute evolution metrics:
    - stability score (fraction of time fingerprint unchanged)
    - mutation rate (changes per tick)
    - unique states count
    """
    if not fingerprints:
        return {}
    changes = sum(1 for i in range(1, len(fingerprints)) if fingerprints[i] != fingerprints[i - 1])
    unique  = len(set(fingerprints))
    return {
        "total_ticks":    len(fingerprints),
        "unique_states":  unique,
        "stability":      round(1 - changes / max(len(fingerprints), 1), 4),
        "mutation_rate":  round(changes / max(len(fingerprints) - 1, 1), 4),
        "recent": fingerprints[-10:],
    }


def detect_anomaly(current_fp: str, history: List[str], threshold: float = 0.25) -> Dict:
    """
    Compare current fingerprint against recent history.
    If similarity to all recent states is below threshold → anomaly detected.
    """
    if not history:
        return {"anomaly": False, "reason": "No history available"}
    similarities = [fingerprint_similarity(current_fp, h) for h in history[-10:]]
    max_sim = max(similarities)
    avg_sim = sum(similarities) / len(similarities)
    anomaly = avg_sim < threshold
    return {
        "anomaly":          anomaly,
        "max_similarity":   round(max_sim, 4),
        "avg_similarity":   round(avg_sim, 4),
        "reason":           "State significantly different from recent history" if anomaly else "Normal state",
    }

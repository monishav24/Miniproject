"""
evaluation.py
Evaluates a UPF placement by computing latency, energy, and SLA violations.
"""
import networkx as nx


def evaluate_placement(G, users, upfs):
    """
    For each user, finds the nearest UPF (shortest weighted path).
    Returns: (avg_latency_ms, total_energy, sla_violation_count)
    """
    total_latency = 0.0
    sla_violations = 0
    energy = len(upfs) * 50.0  # Base cost per active UPF

    for u in users:
        min_dist = float('inf')
        for upf in upfs:
            try:
                d = nx.shortest_path_length(G, u.current_node, upf, weight='weight')
                min_dist = min(min_dist, d)
            except nx.NetworkXNoPath:
                pass

        if min_dist == float('inf'):
            min_dist = 100  # Penalty for unreachable

        latency = min_dist * 2.0  # 2 ms per weight unit
        total_latency += latency
        energy += latency * 0.1

        if latency > u.req_latency:
            sla_violations += 1

    avg_latency = total_latency / max(1, len(users))
    return avg_latency, energy, sla_violations

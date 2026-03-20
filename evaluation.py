import networkx as nx

def evaluate_placement(G, users, upfs):
    """
    Evaluates the current placement strategy.
    Calculates average latency, total energy consumed, and SLA violations.
    """
    total_latency = 0
    sla_violations = 0
    # Base energy cost for active UPFs
    energy = len(upfs) * 50 
    
    for u in users:
        # Find shortest path length to the nearest UPF
        min_dist = float('inf')
        for upf in upfs:
            try:
                dist = nx.shortest_path_length(G, u.current_node, upf, weight='weight')
                if dist < min_dist:
                    min_dist = dist
            except nx.NetworkXNoPath:
                pass
        
        if min_dist == float('inf'):
            min_dist = 100  # Penalty for unreachable node
            
        latency = min_dist * 2  # Assuming 2ms latency per unit weight
        total_latency += latency
        
        energy += latency * 0.1  # Distance-based transmission energy cost
        
        if latency > u.req_latency:
            sla_violations += 1
            
    avg_latency = total_latency / max(1, len(users))
    return avg_latency, energy, sla_violations

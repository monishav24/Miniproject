def calculate_cost(latency, energy, sla_violations, alpha=0.4, beta=0.3, gamma=0.3):
    """
    Cost function C = αL + βE + γ·SLA
    """
    return alpha * latency + beta * energy + gamma * sla_violations

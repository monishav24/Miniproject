"""
cost_function.py
Calculates the composite operational cost:
    C = α·Latency + β·Energy + γ·SLA_violations
"""


def calculate_cost(latency, energy, sla_violations,
                   alpha=0.4, beta=0.3, gamma=0.3):
    """Returns the weighted operational cost."""
    return alpha * latency + beta * energy + gamma * sla_violations

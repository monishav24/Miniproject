"""
traffic_model.py
Generates users with eMBB, URLLC, and mMTC traffic profiles.
Each traffic type has a different SLA latency requirement.
"""
import random


class User:
    """Represents a mobile user attached to a network node."""

    TRAFFIC_PROFILES = {
        'URLLC': {'req_latency': 10, 'priority': 3},
        'eMBB':  {'req_latency': 40, 'priority': 2},
        'mMTC':  {'req_latency': 100, 'priority': 1},
    }

    def __init__(self, user_id, start_node):
        self.user_id = user_id
        self.current_node = start_node
        self.traffic_type = random.choice(list(self.TRAFFIC_PROFILES.keys()))
        profile = self.TRAFFIC_PROFILES[self.traffic_type]
        self.req_latency = profile['req_latency']
        self.priority = profile['priority']


def generate_users(G, num_users=100):
    """Creates a list of users randomly distributed across graph nodes."""
    nodes = list(G.nodes())
    return [User(i, random.choice(nodes)) for i in range(num_users)]

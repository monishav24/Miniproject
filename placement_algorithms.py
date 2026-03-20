"""
placement_algorithms.py
Implements five UPF placement strategies:
  1. Static   – betweenness centrality (computed once)
  2. Random   – random node selection
  3. Greedy   – based on current user distribution
  4. Predictive – based on forecasted user locations
  5. Q-Learning – tabular reinforcement learning
"""
import networkx as nx
import random
from collections import defaultdict


# ---------------------------------------------------------------------------
# 1. Static Placement
# ---------------------------------------------------------------------------
def static_placement(G, num_upfs=5):
    """Places UPFs at the nodes with highest betweenness centrality."""
    centrality = nx.betweenness_centrality(G, weight='weight')
    sorted_nodes = sorted(centrality, key=centrality.get, reverse=True)
    return sorted_nodes[:num_upfs]


# ---------------------------------------------------------------------------
# 2. Random Placement
# ---------------------------------------------------------------------------
def random_placement(G, num_upfs=5):
    """Places UPFs at randomly chosen nodes."""
    return random.sample(list(G.nodes()), num_upfs)


# ---------------------------------------------------------------------------
# 3. Greedy Placement
# ---------------------------------------------------------------------------
def greedy_placement(G, users, num_upfs=5):
    """Places UPFs at nodes that currently host the most users."""
    counts = defaultdict(int)
    for u in users:
        counts[u.current_node] += 1
    sorted_nodes = sorted(G.nodes(), key=lambda n: counts[n], reverse=True)
    return sorted_nodes[:num_upfs]


# ---------------------------------------------------------------------------
# 4. Predictive Placement
# ---------------------------------------------------------------------------
def predictive_placement(G, predicted_nodes, num_upfs=5):
    """Places UPFs at nodes predicted to host the most users in the future."""
    counts = defaultdict(int)
    for uid, node in predicted_nodes.items():
        counts[node] += 1
    sorted_nodes = sorted(G.nodes(), key=lambda n: counts[n], reverse=True)
    return sorted_nodes[:num_upfs]


# ---------------------------------------------------------------------------
# 5. Q-Learning Placement
# ---------------------------------------------------------------------------
class QLearningPlacement:
    """
    Tabular Q-Learning agent for UPF placement.
    State  = tuple(sorted current UPF positions)
    Action = a new tuple of UPF positions
    Reward = −cost  (lower cost → higher reward)
    """

    def __init__(self, num_nodes, num_upfs=5, alpha=0.1, gamma_rl=0.9,
                 epsilon_start=1.0, epsilon_min=0.05, epsilon_decay=0.995):
        self.num_nodes = num_nodes
        self.num_upfs = num_upfs
        self.alpha = alpha
        self.gamma_rl = gamma_rl
        self.epsilon = epsilon_start
        self.epsilon_min = epsilon_min
        self.epsilon_decay = epsilon_decay
        self.q_table = {}

    def _state_key(self, upfs):
        return tuple(sorted(upfs))

    def get_action(self, current_upfs):
        """Epsilon-greedy action selection."""
        state = self._state_key(current_upfs)
        if random.random() < self.epsilon:
            # Explore: pick random UPF set
            return random.sample(range(self.num_nodes), self.num_upfs)
        if state in self.q_table:
            best = max(self.q_table[state], key=self.q_table[state].get)
            return list(best)
        return random.sample(range(self.num_nodes), self.num_upfs)

    def update(self, old_upfs, new_upfs, reward):
        """Update Q-value for (state, action) pair."""
        state = self._state_key(old_upfs)
        action = self._state_key(new_upfs)
        if state not in self.q_table:
            self.q_table[state] = {}
        old_q = self.q_table[state].get(action, 0.0)
        # Simple Q-update (no next-state max in this simplified version)
        self.q_table[state][action] = old_q + self.alpha * (reward - old_q)
        # Decay epsilon
        self.epsilon = max(self.epsilon_min, self.epsilon * self.epsilon_decay)

    def get_placement(self, current_upfs):
        """Convenience wrapper returning a list of UPF node IDs."""
        return self.get_action(current_upfs)

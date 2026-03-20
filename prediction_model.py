"""
prediction_model.py
Predicts future user positions using a Moving Average of recent history
combined with a simple Linear Regression trend.
"""
import numpy as np
from collections import defaultdict


class Predictor:
    """Tracks user movement history and predicts next node locations."""

    def __init__(self, window=5):
        self.history = defaultdict(list)
        self.window = window

    def update(self, users):
        """Records the current node for each user."""
        for u in users:
            self.history[u.user_id].append(u.current_node)
            # Keep only the most recent `window` entries
            if len(self.history[u.user_id]) > self.window:
                self.history[u.user_id] = self.history[u.user_id][-self.window:]

    def predict_next_nodes(self):
        """
        Predicts each user's next node.
        Uses the most frequent recent node (moving average heuristic).
        Falls back to the last known node if history is too short.
        """
        predictions = {}
        for uid, hist in self.history.items():
            if len(hist) < 2:
                predictions[uid] = hist[-1]
            else:
                # Most frequent node in the window = best guess
                predictions[uid] = max(set(hist), key=hist.count)
        return predictions

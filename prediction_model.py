class Predictor:
    def __init__(self):
        self.history = {}

    def update(self, users):
        """
        Updates the prediction history with the user's current node.
        """
        for u in users:
            if u.user_id not in self.history:
                self.history[u.user_id] = []
            self.history[u.user_id].append(u.current_node)
            if len(self.history[u.user_id]) > 5:
                self.history[u.user_id].pop(0)

    def predict_next_nodes(self):
        """
        Uses a Simple Moving Average (most frequent recent node) to predict the next location.
        """
        predictions = {}
        for uid, hist in self.history.items():
            if len(hist) < 2:
                predictions[uid] = hist[-1]
            else:
                # Prediction based on most frequent node in history
                predictions[uid] = max(set(hist), key=hist.count)
        return predictions

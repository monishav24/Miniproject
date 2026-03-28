"""
Prediction Engine — ARIMA-based per-node congestion forecasting
"""
import warnings
from collections import deque
from typing import Dict, List

import numpy as np

try:
    from statsmodels.tsa.arima.model import ARIMA
    ARIMA_AVAILABLE = True
except ImportError:
    ARIMA_AVAILABLE = False

HISTORY_LEN  = 60   # minimum ticks of history before ARIMA fires
FORECAST_HORIZON = 10  # ticks ahead to forecast


class CongestionPredictor:
    """
    Maintains rolling per-node load histories and forecasts congestion probability.
    """
    def __init__(self, node_ids: List[int]):
        self._histories: Dict[int, deque] = {
            nid: deque(maxlen=120) for nid in node_ids
        }
        self._forecast_cache: Dict[int, float] = {nid: 0.0 for nid in node_ids}
        self._edge_histories: Dict[tuple, deque] = {}

    def ingest_snapshot(self, snapshot: dict):
        for node in snapshot.get("nodes", []):
            nid = node["id"]
            if nid in self._histories:
                self._histories[nid].append(node["load"])
        for edge in snapshot.get("edges", []):
            key = (edge["source"], edge["target"])
            if key not in self._edge_histories:
                self._edge_histories[key] = deque(maxlen=120)
            self._edge_histories[key].append(edge["utilization"])

    def predict(self) -> Dict:
        """
        Returns per-node congestion probability (0–1) for next FORECAST_HORIZON ticks.
        Falls back to exponential smoothing if ARIMA unavailable or history too short.
        """
        node_probs   = {}
        node_forecasts = {}

        for nid, hist in self._histories.items():
            series = list(hist)
            if len(series) < 10:
                prob = series[-1] if series else 0.0
                node_probs[nid]    = round(min(1.0, prob), 4)
                node_forecasts[nid] = [round(min(1.0, prob), 4)] * FORECAST_HORIZON
                continue

            if ARIMA_AVAILABLE and len(series) >= HISTORY_LEN:
                try:
                    with warnings.catch_warnings():
                        warnings.simplefilter("ignore")
                        model  = ARIMA(series, order=(2, 0, 2))
                        fitted = model.fit()
                        fc     = fitted.forecast(steps=FORECAST_HORIZON)
                        fc_clipped = [round(min(1.0, max(0.0, float(v))), 4) for v in fc]
                        node_probs[nid]    = fc_clipped[-1]   # end-of-horizon probability
                        node_forecasts[nid] = fc_clipped
                        self._forecast_cache[nid] = node_probs[nid]
                        continue
                except Exception:
                    pass

            # Exponential smoothing fallback
            alpha  = 0.3
            smooth = series[0]
            for v in series[1:]:
                smooth = alpha * v + (1 - alpha) * smooth
            # Add trend component
            if len(series) >= 5:
                trend = (series[-1] - series[-5]) / 5.0
            else:
                trend = 0.0
            fc_smooth = [
                round(min(1.0, max(0.0, smooth + trend * i)), 4)
                for i in range(1, FORECAST_HORIZON + 1)
            ]
            node_probs[nid]    = fc_smooth[-1]
            node_forecasts[nid] = fc_smooth

        # Edge congestion predictions
        edge_probs = {}
        for key, hist in self._edge_histories.items():
            series = list(hist)
            if not series:
                edge_probs[str(key)] = 0.0
                continue
            alpha  = 0.3
            smooth = series[0]
            for v in series[1:]:
                smooth = alpha * v + (1 - alpha) * smooth
            edge_probs[str(key)] = round(min(1.0, max(0.0, smooth)), 4)

        return {
            "node_congestion_probability": node_probs,
            "node_forecasts":              node_forecasts,
            "edge_congestion_probability": edge_probs,
            "horizon_ticks":               FORECAST_HORIZON,
            "method": "ARIMA" if ARIMA_AVAILABLE else "ExponentialSmoothing",
        }

    def get_hotspots(self, threshold: float = 0.7) -> List[Dict]:
        """Return nodes predicted to exceed threshold congestion."""
        result = self.predict()
        hotspots = []
        for nid, prob in result["node_congestion_probability"].items():
            if prob >= threshold:
                hotspots.append({
                    "node_id":    nid,
                    "probability": prob,
                    "severity": "critical" if prob >= 0.9 else "high",
                })
        hotspots.sort(key=lambda x: x["probability"], reverse=True)
        return hotspots


# Module-level singleton (initialized lazily)
_predictor: CongestionPredictor = None


def get_predictor(node_ids: List[int] = None) -> CongestionPredictor:
    global _predictor
    if _predictor is None:
        if node_ids is None:
            from backend.collector.traffic_generator import NODE_META
            node_ids = list(NODE_META.keys())
        _predictor = CongestionPredictor(node_ids)
    return _predictor

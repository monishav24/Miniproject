import random
import numpy as np
from datetime import datetime
from typing import Dict, Any

class AnalyticsEngine:
    """
    Production-grade AI Analytics Engine for V2X.
    This simulates a risk model that predicts collision probability 
    and unsafe driving scores based on telemetry.
    """
    
    @staticmethod
    def calculate_risk_scores(telemetry_data: Dict[str, Any]) -> Dict[str, float]:
        """
        Calculates collision probability and unsafe driving score.
        Incorporates acceleration and gyro for higher fidelity.
        """
        speed = telemetry_data.get("speed", 0)
        accel = abs(telemetry_data.get("acceleration", 0))
        gyro = abs(telemetry_data.get("gyro", 0))
        
        # Risk increases with speed, sudden acceleration/braking, and sharp turns
        base_risk = (speed / 120.0) * 0.4
        accel_risk = (accel / 10.0) * 0.3
        gyro_risk = (gyro / 5.0) * 0.3
        
        collision_prob = min(1.0, base_risk + accel_risk + gyro_risk + random.uniform(0, 0.1))
        
        # Unsafe score calculation
        unsafe_score = min(100.0, (speed / 1.2) + (accel * 5) + (gyro * 10) + random.uniform(0, 10))
        
        return {
            "collision_probability": round(collision_prob, 4),
            "unsafe_score": round(unsafe_score, 2)
        }

    @staticmethod
    def predict_path(telemetry_data: Dict[str, Any]) -> List[Dict[str, float]]:
        """
        Predicts the next 5 seconds of the vehicle's path.
        (Linear extrapolation for this implementation)
        """
        lat = telemetry_data.get("latitude", 0)
        lon = telemetry_data.get("longitude", 0)
        speed = telemetry_data.get("speed", 0) / 3.6 # m/s
        heading = telemetry_data.get("heading", 0)
        
        path = []
        for i in range(1, 6):
            # Very simplified projection
            path.append({
                "latitude": lat + (i * 0.0001 * np.cos(np.radians(heading))),
                "longitude": lon + (i * 0.0001 * np.sin(np.radians(heading)))
            })
        return path

analytics_engine = AnalyticsEngine()

import math
from datetime import datetime
from typing import List, Dict, Tuple

class AIRiskEngine:
    """
    Lightweight AI Risk Engine for V2X Collision Prediction.
    Uses trajectory estimation and proximity analysis to calculate risk.
    """
    
    @staticmethod
    def estimate_collision_probability(
        target_telemetry: Dict, 
        nearby_vehicles_telemetry: List[Dict]
    ) -> Tuple[float, str]:
        """
        Calculates collision probability based on speed, heading, and distance.
        """
        if not nearby_vehicles_telemetry:
            return 0.0, "SAFE"
            
        max_prob = 0.0
        
        for other in nearby_vehicles_telemetry:
            # Simple distance calculation (Haversine approximation for small scales)
            dist = AIRiskEngine._calculate_distance(
                target_telemetry['lat'], target_telemetry['lng'],
                other['lat'], other['lng']
            )
            
            # If vehicles are very close (e.g., < 10 meters)
            if dist < 0.01: # 10 meters approx
                prob = 0.85
            elif dist < 0.05: # 50 meters
                prob = 0.45
            else:
                prob = 0.05
                
            # Speed factor: Higher speed increase risk if distance is low
            speed_factor = (target_telemetry['speed'] + other['speed']) / 200.0
            prob = min(1.0, prob + speed_factor)
            
            if prob > max_prob:
                max_prob = prob
                
        status = "SAFE"
        if max_prob > 0.7:
            status = "DANGER"
        elif max_prob > 0.4:
            status = "WARNING"
            
        return max_prob, status

    @staticmethod
    def _calculate_distance(lat1, lon1, lat2, lon2):
        # Rough distance in km (can be improved with Haversine)
        return math.sqrt((lat1 - lat2)**2 + (lon1 - lon2)**2) * 111.0

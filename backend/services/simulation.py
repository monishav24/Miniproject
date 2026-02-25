import asyncio
import random
import time
import math
from datetime import datetime
from typing import Dict, List
import httpx

class V2XSimulator:
    """
    Simulation Engine for 50+ virtual vehicles.
    Generates telemetry and sends it to the API.
    """
    
    def __init__(self, api_url: str, vehicle_count: int = 50):
        self.api_url = api_url
        self.vehicle_count = vehicle_count
        self.is_running = False
        self.vehicles = []
        self._init_vehicles()

    def _init_vehicles(self):
        # Initial positions around a demo coordinate (e.g., San Francisco)
        base_lat, base_lng = 37.7749, -122.4194
        for i in range(self.vehicle_count):
            self.vehicles.append({
                "id": i + 1,
                "name": f"Sim-Vehicle-{i+1}",
                "lat": base_lat + (random.random() - 0.5) * 0.05,
                "lng": base_lng + (random.random() - 0.5) * 0.05,
                "speed": random.randint(30, 80),
                "heading": random.randint(0, 359),
                "acceleration": random.uniform(-2, 2)
            })

    async def start(self):
        self.is_running = True
        print(f"Starting simulation of {self.vehicle_count} vehicles...")
        while self.is_running:
            await self._update_and_send()
            await asyncio.sleep(1) # 1Hz update

    def stop(self):
        self.is_running = False
        print("Simulation stopped.")

    async def _update_and_send(self):
        async with httpx.AsyncClient() as client:
            tasks = []
            for v in self.vehicles:
                # Update positions
                # Speed is in km/h, convert to deg/s (approx 111km per degree)
                lat_change = (float(v['speed']) / 3600.0 / 111.0) * math.cos(math.radians(float(v['heading'])))
                lng_change = (float(v['speed']) / 3600.0 / 111.0) * math.sin(math.radians(float(v['heading'])))
                
                v['lat'] = float(v['lat']) + lat_change
                v['lng'] = float(v['lng']) + lng_change
                
                # Random fluctuations
                v['speed'] = max(0.0, float(v['speed']) + random.uniform(-2.0, 2.0))
                if random.random() > 0.95:
                    v['heading'] = (float(v['heading']) + random.randint(-45, 45)) % 360.0
                
                payload = {
                    "vehicle_id": int(v['id']),
                    "timestamp": datetime.utcnow().isoformat(),
                    "latitude": float(v['lat']),
                    "longitude": float(v['lng']),
                    "speed": round(float(v['speed']), 2),
                    "acceleration": round(float(v['acceleration']), 2),
                    "heading": float(v['heading'])
                }
                # Fix: Use the correct API URL from initialization
                tasks.append(client.post(f"{self.api_url}/telemetry", json=payload))
            
            # Batch send
            await asyncio.gather(*tasks, return_exceptions=True)

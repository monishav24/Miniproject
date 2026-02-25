import asyncio
import random
import time
import math
from datetime import datetime
from typing import Dict, List
import httpx

class V2XSimulator:
    """
    Simulation Engine for dynamic vehicle sets.
    Generates telemetry and sends it to the API.
    """
    
    def __init__(self, api_url: str):
        self.api_url = api_url
        self.is_running = False
        self.vehicles: List[Dict] = []
        self._lock = asyncio.Lock()

    async def start(self, vehicle_list: List[Dict]):
        """
        Starts simulation for the provided list of vehicles.
        Expects [{'id': 1, 'name': 'V1', 'lat': 37..., 'lng': -122...}]
        """
        async with self._lock:
            if self.is_running:
                # Merge or replace? Let's replace for simplicity
                self.vehicles = vehicle_list
                return
            
            self.vehicles = vehicle_list
            self.is_running = True
        
        print(f"🚀 Starting simulation for {len(self.vehicles)} vehicles...")
        try:
            while self.is_running:
                async with self._lock:
                    if not self.vehicles:
                        break
                    await self._update_and_send()
                await asyncio.sleep(1) # 1Hz update
        finally:
            self.is_running = False
            print("🛑 Simulation stopped.")

    def update_vehicles(self, vehicle_list: List[Dict]):
        """Updates the active fleet without restarting the loop."""
        self.vehicles = vehicle_list

    def stop(self):
        self.is_running = False

    async def _update_and_send(self):
        async with httpx.AsyncClient() as client:
            tasks = []
            for v in self.vehicles:
                # Ensure state exists
                if 'speed' not in v: v['speed'] = 40.0
                if 'heading' not in v: v['heading'] = 90.0
                if 'lat' not in v: v['lat'] = 37.7749
                if 'lng' not in v: v['lng'] = -122.4194
                if 'acceleration' not in v: v['acceleration'] = 0.0

                # Update positions (Speed km/h -> deg/s approx)
                lat_change = (float(v['speed']) / 3600.0 / 111.0) * math.cos(math.radians(float(v['heading'])))
                lng_change = (float(v['speed']) / 3600.0 / 111.0) * math.sin(math.radians(float(v['heading'])))
                
                v['lat'] = float(v['lat']) + lat_change
                v['lng'] = float(v['lng']) + lng_change
                
                # Random fluctuations
                v['speed'] = float(max(0.0, float(v['speed']) + random.uniform(-1.5, 1.5)))
                if random.random() > 0.90:
                    v['heading'] = (float(v['heading']) + random.randint(-30, 30)) % 360.0
                
                payload = {
                    "vehicle_id": int(v['id']),
                    "timestamp": datetime.utcnow().isoformat(),
                    "latitude": float(v['lat']),
                    "longitude": float(v['lng']),
                    "speed": float(round(float(v['speed']), 2)),
                    "acceleration": float(round(float(v['acceleration']), 2)),
                    "heading": float(v['heading'])
                }
                tasks.append(client.post(f"{self.api_url}/telemetry", json=payload))
            
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)

import time
import json
import random
import requests
import math
import os
from datetime import datetime

# --- Environment Configuration ---
# API_URL should point to the telemetry endpoint
DEFAULT_API = "http://localhost:3000/telemetry"
API_URL = os.getenv("V2X_API_URL", DEFAULT_API)
VEHICLE_ID = os.getenv("V2X_VEHICLE_ID", "OBU-PI-01")
AUTH_TOKEN = os.getenv("V2X_AUTH_TOKEN", "") # Optional JWT
SEND_INTERVAL = float(os.getenv("V2X_INTERVAL", "1.0"))

class OBUSender:
    def __init__(self, vehicle_id, api_url, token=None):
        self.vehicle_id = vehicle_id
        self.api_url = api_url
        self.token = token
        self.session = requests.Session()
        if token:
            self.session.headers.update({"Authorization": f"Bearer {token}"})
        
        # State for mock data generation
        self.lat = 37.7749
        self.lon = -122.4194
        self.speed = 40.0 # km/h
        self.heading = 90.0 # degrees
        
    def generate_mock_telemetry(self):
        """Generates realistic mock GPS and IMU data."""
        speed_mps = self.speed / 3.6
        # Move vehicle based on heading
        self.lat += (speed_mps * math.cos(math.radians(self.heading)) * 0.000009)
        self.lon += (speed_mps * math.sin(math.radians(self.heading)) * 0.000009)
        
        acceleration = random.uniform(-1.5, 1.5)
        self.speed = float(max(0.0, min(120.0, float(self.speed) + acceleration)))
        
        gyro = random.uniform(-0.1, 0.1)
        self.heading = (self.heading + gyro * 10) % 360
        
        return {
            "vehicle_id": self.vehicle_id,
            "latitude": round(self.lat, 6),
            "longitude": round(self.lon, 6),
            "speed": round(self.speed, 2),
            "heading": round(self.heading, 2),
            "acceleration": round(acceleration, 2),
            "timestamp": datetime.utcnow().timestamp()
        }

    def run(self):
        print(f"🚀 V2X Edge Node Started: {self.vehicle_id}")
        print(f"📡 Target Uplink: {self.api_url}")
        
        while True:
            data = self.generate_mock_telemetry()
            try:
                # Use json=data to send as application/json
                response = self.session.post(self.api_url, json=data, timeout=5)
                
                if response.status_code == 200:
                    res = response.json()
                    status = res.get('status', 'OK')
                    risk = res.get('risk_score', 0)
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] Uplink OK | Risk: {risk:.2f} | Status: {status}")
                elif response.status_code == 401:
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] Auth Error: Check V2X_AUTH_TOKEN")
                    time.sleep(10) # Back off on auth error
                else:
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] Server Error: {response.status_code}")
            except requests.exceptions.RequestException as e:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] Connectivity Loss: Retrying in 5s...")
                time.sleep(5)
                
            time.sleep(SEND_INTERVAL)

if __name__ == "__main__":
    sender = OBUSender(VEHICLE_ID, API_URL, AUTH_TOKEN)
    sender.run()

import time
import json
import random
import requests
import math
from datetime import datetime

# --- Configuration ---
API_URL = "http://localhost:3000/backend/api/telemetry/live" # Update for production
VEHICLE_ID = 1 # Update with registered vehicle ID
SEND_INTERVAL = 1.0 # seconds

class OBUSender:
    def __init__(self, vehicle_id, api_url):
        self.vehicle_id = vehicle_id
        self.api_url = api_url
        self.session = requests.Session()
        
        # State for mock data generation
        self.lat = 37.7749
        self.lon = -122.4194
        self.speed = 40.0 # km/h
        self.heading = 90.0 # degrees
        
    def generate_mock_telemetry(self):
        """Generates realistic mock GPS and IMU data."""
        # Update position based on speed and heading
        # (Very simplified flat-earth projection)
        speed_mps = self.speed / 3.6
        self.lat += (speed_mps * math.cos(math.radians(self.heading)) * 0.000009)
        self.lon += (speed_mps * math.sin(math.radians(self.heading)) * 0.000009)
        
        # Add some jitter to speed and acceleration
        acceleration = random.uniform(-2.0, 2.0)
        self.speed = max(0, self.speed + acceleration)
        
        gyro = random.uniform(-0.5, 0.5)
        self.heading = (self.heading + gyro * 5) % 360
        
        return {
            "vehicle_id": self.vehicle_id,
            "latitude": round(self.lat, 6),
            "longitude": round(self.lon, 6),
            "speed": round(self.speed, 2),
            "heading": round(self.heading, 2),
            "acceleration": round(acceleration, 2),
            "gyro": round(gyro, 2),
            "timestamp": datetime.utcnow().isoformat()
        }

    def run(self):
        print(f"🚀 Starting OBU Telemetry Stream for Vehicle #{self.vehicle_id}")
        print(f"Target API: {self.api_url}")
        
        while True:
            data = self.generate_mock_telemetry()
            try:
                response = self.session.post(self.api_url, json=data, timeout=2)
                if response.status_code == 200:
                    result = response.json()
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] OK | Status: {result['status']} | ID: {result['telemetry_id']}")
                else:
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] Error: {response.status_code}")
            except requests.exceptions.RequestException as e:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] Connection failed: {e}")
                time.sleep(2) # Wait before retry
                
            time.sleep(SEND_INTERVAL)

if __name__ == "__main__":
    sender = OBUSender(VEHICLE_ID, API_URL)
    sender.run()

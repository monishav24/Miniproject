# Raspberry Pi OBU Setup Guide

This guide explains how to set up and run the `pi_sender.py` script on a Raspberry Pi to stream live telemetry to the SmartV2X platform.

## 1. Prerequisites
- Raspberry Pi (3/4/5 or Zero W) with Raspberry Pi OS.
- Python 3.7+ installed.
- Internet connectivity.

## 2. Installation
1. Copy `pi_sender.py` to your Raspberry Pi.
2. Install required dependencies:
   ```bash
   pip3 install requests
   ```

## 3. Configuration
Open `pi_sender.py` and update the following variables:
- `API_URL`: Set this to your deployed backend URL (e.g., `https://your-app.render.com/backend/api/telemetry/live`).
- `VEHICLE_ID`: Set this to the ID of the vehicle you registered on the dashboard.
- `SEND_INTERVAL`: Adjust the frequency of data transmission (default is 1.0 second).

## 4. Running the Script
Execute the script using Python:
```bash
python3 pi_sender.py
```

The script will begin generating mock GPS/IMU data and streaming it to the platform. You should see live updates on your dashboard map and vehicle stats.

## 5. Auto-Start (Optional)
To run the script automatically on boot, add it to your `crontab`:
1. Open crontab: `crontab -e`
2. Add the following line to the end:
   ```bash
   @reboot /usr/bin/python3 /home/pi/pi_sender.py > /home/pi/v2x.log 2>&1
   ```

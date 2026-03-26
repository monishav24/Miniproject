# Real-Time Dynamic UPF Placement in 5G Core Networks

A live simulation dashboard where **Wireshark traffic directly drives UPF (User Plane Function) placement decisions** in a 5G Core network.

## Architecture

```
backend/  → FastAPI + pyshark + NetworkX
frontend/ → React + Vite + Tailwind + react-force-graph-2d
```

## Quick Start

### 1. Backend

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload
```

> **Wireshark**: Backend auto-detects your Wi-Fi/Ethernet interface.  
> Falls back to **simulated traffic** if live capture is unavailable.

### 2. Frontend

```bash
cd frontend
npm install
npm run dev
```

Open [http://localhost:5173](http://localhost:5173)

---

## Features

| Feature | Detail |
|---|---|
| Live Traffic | pyshark LiveCapture from Wi-Fi / Ethernet |
| Fallback | Synthetic oscillating traffic if capture fails |
| Network Model | 10-node graph (gNB → MEC → Core) via NetworkX |
| Static UPF | Fixed at Node 6 |
| Dynamic UPF | Minimum-cost placement updated every second |
| Dashboard | Force-directed graph + 4 live Recharts panels |

## Dashboard Panels

1. **Network Graph** — Nodes colored by type, UPF highlighted red, traffic load in yellow  
2. **Latency Chart** — Dynamic vs Static comparison (ms)  
3. **Energy Chart** — Power consumption comparison  
4. **Packet Rate** — Live from Wireshark capture  
5. **Improvement %** — How much dynamic outperforms static  

## Endpoints

| Endpoint | Method | Description |
|---|---|---|
| `/start_capture` | POST | Start simulation + live capture |
| `/stop_capture` | POST | Stop simulation |
| `/data` | GET | Current state (JSON) |
| `/health` | GET | Health check |

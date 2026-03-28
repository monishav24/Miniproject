# Temporal Network Analysis Platform
### *Autonomous Telecom Network Experimentation — Research Prototype*

> **Final-year thesis-level research platform** demonstrating temporal network observation, versioning, root-cause analysis, and autonomous experimentation for 5G/telecom networks.

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    TEMPORAL NETWORK ANALYSIS PLATFORM                       │
├──────────────────────────┬──────────────────────────┬───────────────────────┤
│       BACKEND (Python)   │   DATABASE (SQLite)      │  FRONTEND (React/TS)  │
│                          │                          │                       │
│  ┌─────────────────────┐ │  ┌────────────────────┐ │  ┌─────────────────┐  │
│  │ Traffic Collector   │ │  │ network_snapshots  │ │  │  NOC Dashboard  │  │
│  │ - Sim generator     │ │  │ experiments        │ │  │  - D3 Topology  │  │
│  │ - tshark live cap   │ │  │ (versioned states) │ │  │  - Timeline     │  │
│  └──────────┬──────────┘ │  └────────────────────┘ │  │  - RCA Panel   │  │
│             │            │                          │  │  - Arch Sim    │  │
│  ┌──────────▼──────────┐ │  ┌────────────────────┐ │  │  - Experiments │  │
│  │ Replay Engine       │ │  │ Fingerprint Store  │ │  │  - Heatmaps    │  │
│  │ (rewind/forward)    │ │  └────────────────────┘ │  └─────────────────┘  │
│  └──────────┬──────────┘ │                          │                       │
│             │            │                          │  ┌─────────────────┐  │
│  ┌──────────▼──────────┐ │                          │  │  WebSocket Hook │  │
│  │ Analysis Engine     │ │                          │  │  (real-time)    │  │
│  │ - RCA (betweenness) │ │                          │  └─────────────────┘  │
│  │ - DNA Fingerprint   │ │                          │                       │
│  │ - Recommender       │ │                          │                       │
│  └──────────┬──────────┘ │                          │                       │
│             │            │                          │                       │
│  ┌──────────▼──────────┐ │                          │                       │
│  │ Prediction Engine   │ │                          │                       │
│  │ ARIMA / Exp.Smooth  │ │                          │                       │
│  └──────────┬──────────┘ │                          │                       │
│             │            │                          │                       │
│  ┌──────────▼──────────┐ │                          │                       │
│  │ Simulation Engine   │ │                          │                       │
│  │ 7 alt architectures │ │                          │                       │
│  └──────────┬──────────┘ │                          │                       │
│             │            │                          │                       │
│  ┌──────────▼──────────┐ │                          │                       │
│  │ Experiment Runner   │ │                          │                       │
│  │ 6-config suite      │ │                          │                       │
│  └─────────────────────┘ │                          │                       │
└──────────────────────────┴──────────────────────────┴───────────────────────┘
         FastAPI (port 8000) ←──────── WebSocket ──────────→ React (port 5173)
```

---

## Features

| Module | Description |
|--------|-------------|
| **Network State Collector** | 15-node telecom topology (gNB, MEC, Core, Transit). Simulated traffic with configurable surge injection. Falls back gracefully to tshark live capture if Wireshark installed. |
| **Temporal Database** | SQLite-backed versioned snapshot store — "Git for networks". Diff, rollback, timeline. |
| **Replay Engine** | Rewind/fast-forward through network history. Compare any two snapshots side-by-side. |
| **Alternate Architecture Simulator** | Evaluates 7 configurations (OSPF, shortest-path, load-balanced, capacity scaling, extra nodes). Ranked comparison table. |
| **Root Cause Analysis** | Graph-based causal inference using betweenness centrality, overload detection, edge congestion, traffic spike analysis, topology imbalance. Confidence-scored ranked causes. |
| **Congestion Predictor** | ARIMA time-series model (falls back to exponential smoothing). Per-node congestion probability for next 10 ticks. D3 heatmap overlay. |
| **Autonomous Experiment Runner** | Runs 6-configuration experiment suite (baseline, surge, capacity variants). Ranked results saved to DB. |
| **Network DNA Fingerprinting** | SHA-256 based network state fingerprint. Hamming similarity, evolution metrics, anomaly detection. |
| **Design Recommendations** | Confidence-scored improvement suggestions: add node, change routing, redistribute load, upgrade links. |
| **NOC Dashboard** | 3-panel React/TypeScript UI with D3.js animated topology, real-time KPIs, timeline scrubber, and all research panels. |

---

## Quick Start

### Prerequisites
- Python 3.11+
- Node.js 18+
- (Optional) Wireshark with tshark for live capture

### 1. Install Python dependencies
```bash
pip install -r requirements.txt
```

### 2. Install frontend dependencies
```bash
cd frontend
npm install
cd ..
```

### 3. Launch everything
```bash
python launch.py
```

Open: **http://localhost:5173**

---

## Docker (Alternative)

```bash
docker compose -f docker/docker-compose.yml up --build
```

---

## Demo Script (for Panelists)

Follow this sequence to demonstrate the full "wow" factor:

```
1.  Open http://localhost:5173
    → Show live network topology with animated node loads and packet flow

2.  Click "🌡 Heat OFF" → turns ON prediction heatmap overlay
    → Show RED nodes predicted to congest

3.  Click ⚡ (surge button) in the timeline bar
    → Traffic surge injected: nodes turn red, alerts fire

4.  Watch the Analysis Console (left) → RCA tab
    → Root causes auto-detected with confidence scores

5.  Click 🔔 Alerts tab
    → Real-time failure alerts appear

6.  Click the timeline slider and drag LEFT → Rewind to pre-surge state
    → Network returns to calm state

7.  Click ⏮ to go to earliest snapshot
    → See network evolution over time

8.  Right panel → ⚙ Sim tab → "▶ Run Simulation"
    → 7 architecture alternatives evaluated and ranked

9.  Right panel → 🧪 Exp tab → "▶ Run Experiment Suite"
    → 6 experiment configurations run autonomously; ranked results shown

10. Right panel → 💡 Rec tab → "🔄 Refresh"
    → Design improvement recommendations with confidence scores

11. Left panel → 🧬 DNA tab
    → Network DNA fingerprint, anomaly detection, evolution metrics
```

---

## API Documentation

| Endpoint | Method | Description |
|----------|--------|-------------|
| `GET /api/snapshot/latest` | GET | Latest network snapshot |
| `GET /api/snapshot/{id}` | GET | Specific snapshot by ID |
| `GET /api/snapshots` | GET | List all snapshots |
| `GET /api/timeline` | GET | Ordered timeline of snapshots |
| `GET /api/replay/go/{id}` | GET | Jump replay cursor to snapshot |
| `GET /api/replay/rewind` | GET | Rewind N steps |
| `GET /api/replay/forward` | GET | Forward N steps |
| `GET /api/replay/compare/{a}/{b}` | GET | Diff two snapshots |
| `GET /api/simulate/alternatives` | GET | Run alternate architecture sim |
| `GET /api/predict` | GET | Get congestion predictions |
| `GET /api/rca` | GET | Run root cause analysis |
| `GET /api/fingerprint` | GET | Network DNA status |
| `GET /api/recommend` | GET | Design recommendations |
| `POST /api/experiment/run` | POST | Run experiment suite |
| `GET /api/experiments` | GET | List past experiments |
| `POST /api/control/surge` | POST | Inject traffic surge |
| `GET /api/alerts` | GET | Current active alerts |
| `WS /ws` | WS | Real-time snapshot + RCA + alerts stream |

---

## Project Structure

```
.
├── launch.py                       # Unified launcher
├── requirements.txt
├── backend/
│   ├── main.py                     # FastAPI app + WebSocket
│   ├── requirements.txt
│   ├── collector/
│   │   └── traffic_generator.py    # Network state collector
│   ├── database/
│   │   └── db.py                   # SQLite temporal store
│   ├── replay_engine/
│   │   └── replay.py               # Rewind / fast-forward
│   ├── simulation_engine/
│   │   └── simulator.py            # Alternate arch. evaluator
│   ├── prediction_engine/
│   │   └── predictor.py            # ARIMA congestion forecasting
│   ├── analysis_engine/
│   │   ├── rca.py                  # Root cause analysis
│   │   ├── fingerprint.py          # Network DNA
│   │   └── recommender.py          # Design recommendations
│   └── experiment_runner/
│       └── runner.py               # Autonomous experiment suite
├── frontend/
│   ├── package.json
│   ├── vite.config.ts
│   ├── index.html
│   └── src/
│       ├── main.tsx
│       ├── App.tsx                 # NOC Dashboard layout
│       ├── index.css               # Dark NOC theme
│       ├── types.ts                # TypeScript definitions
│       ├── hooks/
│       │   └── useNetworkWS.ts     # WebSocket hook
│       └── components/
│           ├── TopologyView.tsx    # D3.js animated topology
│           ├── RCAPanel.tsx        # Root cause panel
│           ├── AlertsPanel.tsx     # Real-time alerts
│           ├── ArchComparison.tsx  # Architecture simulator panel
│           ├── ExperimentPanel.tsx # Experiment runner panel
│           └── RecommendationPanel.tsx
└── docker/
    └── docker-compose.yml
```

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.11, FastAPI, uvicorn |
| Graph Analysis | NetworkX, NumPy, Pandas |
| Prediction | statsmodels (ARIMA), scikit-learn |
| Database | SQLite (local) |
| Packet Capture | tshark / Wireshark (optional) |
| Frontend | React 18, TypeScript, Vite |
| Visualization | D3.js v7 |
| Streaming | WebSockets |
| Deployment | Docker, Docker Compose |

---

## Research Contributions

This prototype demonstrates:
1. **Temporal network state management** — versioned snapshot store analogous to version control for network behavior
2. **Graph-based causal inference** — betweenness centrality for routing bottleneck detection
3. **Predictive congestion control** — ARIMA-based per-node forecasting with heatmap visualization
4. **Autonomous multi-configuration experimentation** — systematic evaluation of network architectures
5. **Network DNA fingerprinting** — cryptographic state identity for anomaly detection and evolution tracking

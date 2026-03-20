# Predictive Multi-UPF Dynamic Placement in 5G Core Networks

**Latency- and Energy-Aware with QoS and Mobility Support**

A complete, runnable, end-to-end simulation system integrating:
- Python-based control logic (placement algorithms, prediction, evaluation)
- ns-3 network simulation (C++ with FlowMonitor)
- NetAnim visualization (animated packet flow)
- Automated execution pipeline (one command)

---

## Quick Start

### Prerequisites
- **Python 3.8+** with packages: `pip install networkx matplotlib numpy`
- **ns-3** installed at `~/ns-3-dev` (for packet-level simulation)
- **NetAnim** installed at `~/ns-3-dev/netanim` (for animation)

### Run Everything With ONE Command
```bash
python3 main.py
```

This automatically:
1. Runs all 5 placement algorithms (Static, Random, Greedy, Predictive, Q-Learning)
2. Simulates 30 nodes, 100 users, 5 UPFs, 200 time steps
3. Exports `topology_static.json` and `topology_predictive.json`
4. Copies `scratch/upf-sim.cc` to ns-3 and runs the simulation
5. Generates `static.xml` and `predictive.xml` (NetAnim animations)
6. Launches NetAnim automatically
7. Parses `flowmon.xml` for ns-3 measured metrics
8. Generates 4 comparison graphs (auto-opened)
9. Prints a performance summary table with % improvements

> **Note:** If ns-3 / NetAnim are not installed, the Python simulation still runs completely — ns-3 steps are gracefully skipped.

---

## Project Structure
```
├── main.py                  # One-command orchestrator
├── network_model.py         # Barabási–Albert topology + JSON export
├── traffic_model.py         # eMBB / URLLC / mMTC user generation
├── mobility_model.py        # Random walk mobility
├── cost_function.py         # C = αL + βE + γ·SLA
├── prediction_model.py      # Moving Average prediction
├── placement_algorithms.py  # Static, Random, Greedy, Predictive, Q-Learning
├── evaluation.py            # Latency, energy, SLA metrics
├── visualization.py         # 4 matplotlib comparison plots
├── run_pipeline.py          # Optional helper (delegates to main.py)
├── requirements.txt         # Python dependencies
├── scratch/
│   └── upf-sim.cc           # ns-3 C++ simulation script
└── README.md
```

## Output Files (generated at runtime)
| File | Description |
|------|-------------|
| `latency_comparison.png` | Latency over time for all algorithms |
| `energy_comparison.png` | Energy consumption comparison |
| `sla_violation_comparison.png` | SLA violation trends |
| `cost_trend.png` | Composite cost (C = αL + βE + γ·SLA) |
| `topology_static.json` | Static placement topology for ns-3 |
| `topology_predictive.json` | Predictive placement topology for ns-3 |
| `static.xml` | NetAnim animation (Static mode) |
| `predictive.xml` | NetAnim animation (Predictive mode) |
| `flowmon_static.xml` | FlowMonitor results (Static) |
| `flowmon_predictive.xml` | FlowMonitor results (Predictive) |

## NetAnim Visualization
- **RED nodes** = UPFs (User Plane Functions)
- **BLUE nodes** = Users / Routers
- Packet flow is animated between nodes

## Algorithms Compared
1. **Static** — UPFs placed at highest betweenness centrality nodes (once)
2. **Random** — UPFs placed at random nodes each step
3. **Greedy** — UPFs placed where most users currently are
4. **Predictive** — UPFs placed where users are predicted to move
5. **Q-Learning** — Reinforcement learning agent optimizes placement over time

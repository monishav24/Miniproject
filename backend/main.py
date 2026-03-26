"""
Real-Time Dynamic UPF Placement in 5G Core
Backend: FastAPI + pyshark (Wireshark live traffic) + NetworkX
"""

import asyncio
import time
import random
import threading
from collections import deque
from datetime import datetime
from typing import Optional

import networkx as nx
import numpy as np
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

app = FastAPI(title="5G UPF Placement API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Network Graph
# ---------------------------------------------------------------------------

NODE_TYPES = {
    0: "gNB",   # 5G base-station
    1: "gNB",
    2: "gNB",
    3: "MEC",   # Mobile Edge Computing
    4: "MEC",
    5: "MEC",
    6: "Core",  # Core network node
    7: "Core",
    8: "Core",
    9: "Core",
}

EDGE_LIST = [
    (0, 3), (1, 3), (2, 4), (3, 6), (3, 7),
    (4, 7), (4, 8), (5, 8), (5, 9), (6, 9),
    (7, 9), (8, 9),
]

def build_graph() -> nx.Graph:
    G = nx.Graph()
    for n, ntype in NODE_TYPES.items():
        G.add_node(n, type=ntype, latency=0.0, energy=0.0, load=0.0)
    for u, v in EDGE_LIST:
        G.add_edge(u, v,
                   latency=round(random.uniform(1, 8), 2),
                   energy=round(random.uniform(0.5, 3.0), 2))
    return G

# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------

class SimState:
    def __init__(self):
        self.G: nx.Graph = build_graph()
        self.running = False
        self.traffic_load = 0.0
        self.packet_rate = 0.0
        self.avg_pkt_size = 0.0
        self.upf_node_dynamic = 6
        self.upf_node_static = 6        # static UPF fixed at node 6
        self.latency_dynamic = 0.0
        self.latency_static = 0.0
        self.energy_dynamic = 0.0
        self.energy_static = 0.0
        self.improvement = 0.0
        self.history_latency: deque = deque(maxlen=60)
        self.history_energy: deque = deque(maxlen=60)
        self.history_packet_rate: deque = deque(maxlen=60)
        self.history_improvement: deque = deque(maxlen=60)
        self.timestamp = 0
        self._lock = threading.Lock()
        self.capture_thread: Optional[threading.Thread] = None
        self.sim_thread: Optional[threading.Thread] = None
        self.use_live_capture = False
        self._stop_event = threading.Event()

state = SimState()

# ---------------------------------------------------------------------------
# pyshark live capture (with fallback)
# ---------------------------------------------------------------------------

def get_default_interface() -> str:
    """Try common interface names; fall back gracefully."""
    candidates = ["Wi-Fi", "WiFi", "wlan0", "eth0", "Ethernet", "en0", "en1"]
    try:
        import pyshark
        for iface in candidates:
            try:
                cap = pyshark.LiveCapture(interface=iface, bpf_filter="ip", output_file=None)
                cap.close()
                return iface
            except Exception:
                continue
    except ImportError:
        pass
    return ""

def live_capture_loop(iface: str, stop_event: threading.Event):
    """Background thread: capture packets and update state every second."""
    try:
        import pyshark
        cap = pyshark.LiveCapture(interface=iface, bpf_filter="ip")
        bucket_count = 0
        bucket_size = 0
        bucket_start = time.time()

        for pkt in cap.sniff_continuously():
            if stop_event.is_set():
                cap.close()
                break
            now = time.time()
            bucket_count += 1
            try:
                bucket_size += int(pkt.length)
            except Exception:
                bucket_size += 64

            if now - bucket_start >= 1.0:
                pkt_rate = bucket_count / (now - bucket_start)
                avg_size = bucket_size / max(bucket_count, 1)
                with state._lock:
                    state.packet_rate = round(pkt_rate, 2)
                    state.avg_pkt_size = round(avg_size, 1)
                    state.traffic_load = round(min(pkt_rate / 50.0, 1.0) * 10.0, 2)
                bucket_count = 0
                bucket_size = 0
                bucket_start = now
    except Exception as e:
        print(f"[pyshark] capture failed: {e}. Falling back to simulation.")
        with state._lock:
            state.use_live_capture = False

def simulated_traffic_loop(stop_event: threading.Event):
    """Fallback: generate synthetic traffic that oscillates."""
    t = 0
    while not stop_event.is_set():
        t += 1
        # Simulate realistic traffic wave
        base = 5 + 3 * np.sin(t * 0.2)
        spike = random.uniform(0, 4) if random.random() > 0.8 else 0
        pkt_rate = max(0, base + spike + random.gauss(0, 0.5))
        avg_size = random.uniform(200, 1400)
        with state._lock:
            state.packet_rate = round(pkt_rate, 2)
            state.avg_pkt_size = round(avg_size, 1)
            state.traffic_load = round(min(pkt_rate / 20.0, 1.0) * 10.0, 2)
        time.sleep(1.0)

# ---------------------------------------------------------------------------
# UPF Placement Algorithms
# ---------------------------------------------------------------------------

def node_cost(G: nx.Graph, node: int, traffic_load: float) -> float:
    """Compute total cost for placing UPF at a given node."""
    # Sum edge latencies + energy for shortest paths from gNB nodes
    gnb_nodes = [n for n, d in G.nodes(data=True) if d["type"] == "gNB"]
    total_lat = 0.0
    total_eng = 0.0
    for gNB in gnb_nodes:
        try:
            path = nx.shortest_path(G, source=gNB, target=node, weight="latency")
            for i in range(len(path) - 1):
                e = G.edges[path[i], path[i+1]]
                total_lat += e["latency"]
                total_eng += e["energy"]
        except nx.NetworkXNoPath:
            total_lat += 999
    load_factor = traffic_load * 0.5
    return total_lat + total_eng + load_factor

def static_placement(G: nx.Graph) -> int:
    return state.upf_node_static  # always node 6

def dynamic_placement(G: nx.Graph, traffic_load: float) -> int:
    """Choose the node with minimum total cost (excluding gNB nodes)."""
    candidates = [n for n, d in G.nodes(data=True) if d["type"] in ("MEC", "Core")]
    best = min(candidates, key=lambda n: node_cost(G, n, traffic_load))
    return best

def compute_metrics(G: nx.Graph, upf_node: int) -> tuple:
    """Return (latency, energy) for the current UPF placement."""
    gnb_nodes = [n for n, d in G.nodes(data=True) if d["type"] == "gNB"]
    total_lat = 0.0
    total_eng = 0.0
    for gNB in gnb_nodes:
        try:
            path = nx.shortest_path(G, source=gNB, target=upf_node, weight="latency")
            for i in range(len(path) - 1):
                e = G.edges[path[i], path[i+1]]
                total_lat += e["latency"]
                total_eng += e["energy"]
        except nx.NetworkXNoPath:
            total_lat += 999
    return round(total_lat, 2), round(total_eng, 2)

# ---------------------------------------------------------------------------
# Simulation loop
# ---------------------------------------------------------------------------

def simulation_loop(stop_event: threading.Event):
    while not stop_event.is_set():
        with state._lock:
            tl = state.traffic_load
            G = state.G

        # Slightly randomize edge weights over time (network dynamics)
        for u, v in G.edges():
            G.edges[u, v]["latency"] = round(
                max(0.5, G.edges[u, v]["latency"] + random.gauss(0, 0.3)), 2)
            G.edges[u, v]["energy"] = round(
                max(0.1, G.edges[u, v]["energy"] + random.gauss(0, 0.1)), 2)

        upf_dyn = dynamic_placement(G, tl)
        upf_stat = static_placement(G)

        lat_dyn, eng_dyn = compute_metrics(G, upf_dyn)
        lat_stat, eng_stat = compute_metrics(G, upf_stat)

        # Scale metrics slightly with traffic load
        lat_dyn = round(lat_dyn + tl * 0.3, 2)
        lat_stat = round(lat_stat + tl * 0.8, 2)  # static suffers more under load
        eng_dyn = round(eng_dyn + tl * 0.1, 2)
        eng_stat = round(eng_stat + tl * 0.2, 2)

        improvement = 0.0
        if lat_stat > 0:
            improvement = round(((lat_stat - lat_dyn) / lat_stat) * 100, 1)

        with state._lock:
            state.upf_node_dynamic = upf_dyn
            state.latency_dynamic = lat_dyn
            state.latency_static = lat_stat
            state.energy_dynamic = eng_dyn
            state.energy_static = eng_stat
            state.improvement = improvement
            state.timestamp += 1
            state.history_latency.append({"t": state.timestamp, "dynamic": lat_dyn, "static": lat_stat})
            state.history_energy.append({"t": state.timestamp, "dynamic": eng_dyn, "static": eng_stat})
            state.history_packet_rate.append({"t": state.timestamp, "value": state.packet_rate})
            state.history_improvement.append({"t": state.timestamp, "value": improvement})

        time.sleep(1.0)

# ---------------------------------------------------------------------------
# API Endpoints
# ---------------------------------------------------------------------------

@app.post("/start_capture")
def start_simulation():
    if state.running:
        return {"status": "already running"}

    state._stop_event.clear()
    state.running = True

    # Try live capture first
    iface = get_default_interface()
    if iface:
        state.use_live_capture = True
        t = threading.Thread(target=live_capture_loop, args=(iface, state._stop_event), daemon=True)
        state.capture_thread = t
        t.start()
        print(f"[INFO] Live capture started on: {iface}")
    else:
        state.use_live_capture = False
        t = threading.Thread(target=simulated_traffic_loop, args=(state._stop_event,), daemon=True)
        state.capture_thread = t
        t.start()
        print("[INFO] No live interface found. Using simulated traffic.")

    sim_t = threading.Thread(target=simulation_loop, args=(state._stop_event,), daemon=True)
    state.sim_thread = sim_t
    sim_t.start()

    return {"status": "started", "interface": iface or "simulation", "live": bool(iface)}


@app.post("/stop_capture")
def stop_simulation():
    if not state.running:
        return {"status": "not running"}
    state._stop_event.set()
    state.running = False
    return {"status": "stopped"}


@app.get("/data")
def get_data():
    with state._lock:
        G = state.G
        nodes = [
            {
                "id": n,
                "type": d["type"],
                "load": round(state.traffic_load * random.uniform(0.5, 1.0), 2),
            }
            for n, d in G.nodes(data=True)
        ]
        edges = [
            {
                "source": u,
                "target": v,
                "latency": d["latency"],
                "energy": d["energy"],
            }
            for u, v, d in G.edges(data=True)
        ]
        return {
            "nodes": nodes,
            "edges": edges,
            "upf_node": state.upf_node_dynamic,
            "upf_node_static": state.upf_node_static,
            "traffic_load": state.traffic_load,
            "packet_rate": state.packet_rate,
            "avg_pkt_size": state.avg_pkt_size,
            "latency": state.latency_dynamic,
            "latency_static": state.latency_static,
            "energy": state.energy_dynamic,
            "energy_static": state.energy_static,
            "improvement": state.improvement,
            "timestamp": state.timestamp,
            "running": state.running,
            "live_capture": state.use_live_capture,
            "history": {
                "latency": list(state.history_latency),
                "energy": list(state.history_energy),
                "packet_rate": list(state.history_packet_rate),
                "improvement": list(state.history_improvement),
            },
        }


@app.get("/health")
def health():
    return {"status": "ok"}


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)

"""
Network State Collector — Simulated traffic generator + Wireshark fallback
"""
import asyncio
import hashlib
import json
import math
import random
import subprocess
import threading
import time
from collections import deque
from typing import Dict, List, Optional

import networkx as nx
import numpy as np


# ─── Telecom topology (15 nodes) ────────────────────────────────────────────
NODE_META = {
    0:  {"type": "gNB",    "pos": [-4.0,  2.0], "label": "gNB-A"},
    1:  {"type": "gNB",    "pos": [-4.0,  0.0], "label": "gNB-B"},
    2:  {"type": "gNB",    "pos": [-4.0, -2.0], "label": "gNB-C"},
    3:  {"type": "gNB",    "pos": [-2.5,  3.0], "label": "gNB-D"},
    4:  {"type": "MEC",    "pos": [-1.5,  2.0], "label": "MEC-1"},
    5:  {"type": "MEC",    "pos": [-1.5,  0.0], "label": "MEC-2"},
    6:  {"type": "MEC",    "pos": [-1.5, -2.0], "label": "MEC-3"},
    7:  {"type": "Core",   "pos": [ 0.5,  2.5], "label": "Core-A"},
    8:  {"type": "Core",   "pos": [ 0.5,  0.5], "label": "Core-B"},
    9:  {"type": "Core",   "pos": [ 0.5, -1.5], "label": "Core-C"},
    10: {"type": "Transit","pos": [ 2.5,  1.5], "label": "Tran-1"},
    11: {"type": "Transit","pos": [ 2.5, -0.5], "label": "Tran-2"},
    12: {"type": "Core",   "pos": [ 4.0,  2.0], "label": "Core-D"},
    13: {"type": "Core",   "pos": [ 4.0,  0.0], "label": "Core-E"},
    14: {"type": "Core",   "pos": [ 4.0, -1.5], "label": "Core-F"},
}

EDGE_LIST = [
    (0, 4), (1, 4), (1, 5), (2, 5), (2, 6), (3, 4),
    (4, 7), (4, 8), (5, 8), (5, 9), (6, 9),
    (7, 10), (8, 10), (8, 11), (9, 11),
    (10, 12), (10, 13), (11, 13), (11, 14),
    (12, 13), (13, 14),
]


def build_base_graph() -> nx.Graph:
    G = nx.Graph()
    for nid, meta in NODE_META.items():
        G.add_node(nid, **meta, load=0.0)
    for u, v in EDGE_LIST:
        G.add_edge(u, v,
                   latency=round(random.uniform(1.5, 8.0), 2),
                   bandwidth=round(random.uniform(100, 1000), 1),
                   utilization=0.0,
                   packet_drops=0.0)
    return G


class TrafficCollector:
    """
    Manages network state: simulated traffic or live tshark capture.
    Emits snapshots every `interval` seconds.
    """
    HISTORY = 120  # seconds of metric history

    def __init__(self, interval: float = 1.0):
        self.interval = interval
        self.G = build_base_graph()
        self.lock = threading.Lock()
        self._stop = threading.Event()

        # Per-node rolling metrics
        self.node_loads: Dict[int, deque] = {
            n: deque(maxlen=self.HISTORY) for n in NODE_META
        }
        self.edge_utilization: Dict[tuple, deque] = {
            e: deque(maxlen=self.HISTORY) for e in EDGE_LIST
        }
        self.packet_rates: deque = deque(maxlen=self.HISTORY)
        self.latencies: deque   = deque(maxlen=self.HISTORY)
        self.timestamps: deque  = deque(maxlen=self.HISTORY)

        self.live_capture = False
        self._tick = 0
        self._surge_active = False
        self._surge_ticks = 0

        # Callbacks fired each tick
        self._callbacks: List = []

    # ── Public controls ──────────────────────────────────────────────────────
    def start(self):
        iface = self._detect_tshark_iface()
        if iface:
            self.live_capture = True
            t = threading.Thread(target=self._live_thread, args=(iface,), daemon=True)
        else:
            t = threading.Thread(target=self._sim_thread, daemon=True)
        t.start()

    def stop(self):
        self._stop.set()

    def trigger_surge(self, duration: int = 15):
        """Inject a traffic surge for `duration` ticks."""
        self._surge_active = True
        self._surge_ticks  = duration

    def add_callback(self, fn):
        self._callbacks.append(fn)

    # ── Snapshot generation ──────────────────────────────────────────────────
    def get_snapshot(self) -> dict:
        with self.lock:
            nodes = []
            for nid, meta in NODE_META.items():
                load = list(self.node_loads[nid])
                nodes.append({
                    "id":    nid,
                    "label": meta["label"],
                    "type":  meta["type"],
                    "pos":   meta["pos"],
                    "load":  round(load[-1], 3) if load else 0.0,
                    "load_history": list(load)[-10:],
                })
            edges = []
            for u, v in EDGE_LIST:
                data = self.G.edges[u, v]
                util_h = list(self.edge_utilization.get((u, v), []))
                edges.append({
                    "source":      u,
                    "target":      v,
                    "latency":     round(data["latency"], 2),
                    "bandwidth":   round(data["bandwidth"], 1),
                    "utilization": round(data["utilization"], 3),
                    "packet_drops":round(data["packet_drops"], 3),
                    "util_history": util_h[-10:],
                })
            pr = list(self.packet_rates)
            lt = list(self.latencies)
            ts = list(self.timestamps)
            snap = {
                "tick":        self._tick,
                "timestamp":   time.time(),
                "live_capture":self.live_capture,
                "surge_active":self._surge_active,
                "nodes":       nodes,
                "edges":       edges,
                "metrics": {
                    "packet_rate":     round(pr[-1], 2)  if pr else 0.0,
                    "avg_latency":     round(lt[-1], 2)  if lt else 0.0,
                    "packet_rate_hist":pr[-30:],
                    "latency_hist":    lt[-30:],
                    "timestamps":      ts[-30:],
                },
                "fingerprint": self._fingerprint(nodes, edges),
            }
        return snap

    def _fingerprint(self, nodes, edges) -> str:
        data = {
            "loads":   sorted([n["load"] for n in nodes]),
            "latencies": sorted([e["latency"] for e in edges]),
            "utils":   sorted([e["utilization"] for e in edges]),
        }
        raw = json.dumps(data, sort_keys=True).encode()
        return hashlib.sha256(raw).hexdigest()[:16]

    # ── Simulation thread ────────────────────────────────────────────────────
    def _sim_thread(self):
        t = 0
        while not self._stop.is_set():
            t += 1
            self._tick = t

            # Surge handling
            if self._surge_active:
                self._surge_ticks -= 1
                if self._surge_ticks <= 0:
                    self._surge_active = False
                surge_mult = 3.5
            else:
                surge_mult = 1.0

            base_rate = 5.0 + 3.0 * math.sin(t * 0.15) + random.gauss(0, 0.3)
            pkt_rate  = max(0.5, base_rate * surge_mult + random.gauss(0, 0.5))

            with self.lock:
                # Update edge metrics
                for u, v in EDGE_LIST:
                    e = self.G.edges[u, v]
                    e["latency"] = round(max(0.5, e["latency"] + random.gauss(0, 0.25 * surge_mult)), 2)
                    util = min(1.0, (pkt_rate / 20.0) * random.uniform(0.3, 1.2) * surge_mult)
                    e["utilization"] = round(util, 3)
                    e["packet_drops"] = round(max(0.0, (util - 0.7) * 0.3), 3)
                    e["bandwidth"] = round(max(50, e["bandwidth"] + random.gauss(0, 5)), 1)
                    self.edge_utilization[(u, v)].append(util)

                # Update node loads
                for nid in NODE_META:
                    nbr_utils = [self.G.edges[u, v]["utilization"]
                                 for u, v in self.G.edges(nid)
                                 if self.G.has_edge(u, v)]
                    load = min(1.0, (sum(nbr_utils) / max(len(nbr_utils), 1)) * surge_mult * random.uniform(0.8, 1.2))
                    self.node_loads[nid].append(round(load, 3))

                avg_lat = round(sum(self.G.edges[u, v]["latency"] for u, v in EDGE_LIST) / len(EDGE_LIST), 2)
                self.packet_rates.append(round(pkt_rate, 2))
                self.latencies.append(avg_lat)
                self.timestamps.append(t)

            for fn in self._callbacks:
                try:
                    fn(self.get_snapshot())
                except Exception:
                    pass

            time.sleep(self.interval)

    # ── Live capture thread ──────────────────────────────────────────────────
    def _live_thread(self, iface: str):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            import pyshark
            cap = pyshark.LiveCapture(interface=iface, bpf_filter="ip")
            count = 0
            size  = 0
            t0    = time.time()
            for pkt in cap.sniff_continuously():
                if self._stop.is_set():
                    cap.close()
                    break
                count += 1
                try:
                    size += int(pkt.length)
                except Exception:
                    size += 64
                now = time.time()
                if now - t0 >= self.interval:
                    pkt_rate = count / (now - t0)
                    with self.lock:
                        self.packet_rates.append(round(pkt_rate, 2))
                        self._tick += 1
                    count = size = 0
                    t0 = now
                    for fn in self._callbacks:
                        try:
                            fn(self.get_snapshot())
                        except Exception:
                            pass
        except Exception as e:
            print(f"[WARN] Live capture failed: {e}. Switching to simulation.")
            self.live_capture = False
            self._sim_thread()
        finally:
            loop.close()

    # ── Interface detection ──────────────────────────────────────────────────
    @staticmethod
    def _detect_tshark_iface() -> Optional[str]:
        try:
            res = subprocess.run(["tshark", "-D"], capture_output=True, text=True, timeout=10)
            lines = res.stdout.strip().splitlines()
            for kw in ["wi-fi", "wifi", "wlan", "ethernet", "eth"]:
                for line in lines:
                    if kw in line.lower():
                        parts = line.split(None, 1)
                        if len(parts) >= 2:
                            return parts[1].split(" (")[0].strip()
        except Exception:
            pass
        return None

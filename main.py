# -*- coding: utf-8 -*-
"""
Real-Time Dynamic UPF Placement in 5G Core
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Run with:  python main.py

Features:
  • Live packet capture via pyshark (fallback: simulation)
  • NetworkX 10-node 5G topology
  • Dynamic vs Static UPF placement
  • Real-time matplotlib dashboard (4 subplots + network graph)
  • Console metrics every second
"""

# FIX: Import asyncio so we can create a dedicated event loop inside the
# capture thread.  On Windows, background threads have NO default event loop;
# PyShark's sniff_continuously() relies on asyncio internally, so without
# this fix it raises "There is no current event loop in thread …".
import asyncio
import subprocess
import threading
import time
import random
import math
import sys
from collections import deque

import networkx as nx
import numpy as np
import matplotlib
matplotlib.use("TkAgg")           # works on Windows; falls back gracefully
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import matplotlib.patches as mpatches
from matplotlib.animation import FuncAnimation


# ─────────────────────────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────────────────────────
HISTORY_LEN   = 60          # seconds of history shown in charts
UPDATE_INTERVAL_MS = 1000   # animation refresh in ms
STATIC_UPF_NODE  = 6        # fixed node for static placement

IFACE_CANDIDATES = [
    "Wi-Fi", "WiFi", "WLAN", "wlan0",
    "Ethernet", "eth0", "en0", "en1",
    "Local Area Connection",
]

# ─────────────────────────────────────────────────────────────────
# COLOUR PALETTE
# ─────────────────────────────────────────────────────────────────
C_BG      = "#0d1117"
C_PANEL   = "#161b22"
C_BORDER  = "#30363d"
C_TEXT    = "#e6edf3"
C_DIM     = "#8b949e"
C_GREEN   = "#3fb950"
C_RED     = "#f85149"
C_BLUE    = "#58a6ff"
C_ORANGE  = "#d29922"
C_PURPLE  = "#bc8cff"

NODE_COLOURS = {
    "gNB":  "#58a6ff",
    "MEC":  "#3fb950",
    "Core": "#d29922",
}

# ─────────────────────────────────────────────────────────────────
# NETWORK TOPOLOGY
# ─────────────────────────────────────────────────────────────────
NODE_META = {
    # id : (type,  fixed_pos)
    0:  ("gNB",  (-3,  1.5)),
    1:  ("gNB",  (-3,  0.0)),
    2:  ("gNB",  (-3, -1.5)),
    3:  ("MEC",  (-1,  1.0)),
    4:  ("MEC",  (-1, -1.0)),
    5:  ("MEC",  ( 0,  2.0)),
    6:  ("Core", ( 1,  1.5)),
    7:  ("Core", ( 1,  0.0)),
    8:  ("Core", ( 1, -1.5)),
    9:  ("Core", ( 3,  0.0)),
}

EDGE_LIST = [
    (0, 3), (1, 3), (2, 4),
    (3, 5), (3, 6), (3, 7),
    (4, 7), (4, 8),
    (5, 6), (6, 9),
    (7, 9), (8, 9),
]

POS = {n: meta[1] for n, meta in NODE_META.items()}   # fixed layout


def build_graph() -> nx.Graph:
    G = nx.Graph()
    for n, (ntype, _) in NODE_META.items():
        G.add_node(n, type=ntype)
    for u, v in EDGE_LIST:
        G.add_edge(u, v,
                   latency=round(random.uniform(1.5, 8.0), 2),
                   energy =round(random.uniform(0.5, 3.0),  2))
    return G


# ─────────────────────────────────────────────────────────────────
# SHARED STATE
# ─────────────────────────────────────────────────────────────────
class State:
    def __init__(self):
        self.lock         = threading.Lock()
        self.G            = build_graph()

        # Traffic
        self.packet_rate  = 0.0
        self.avg_pkt_size = 0.0
        self.traffic_load = 0.0
        self.live_capture = False

        # UPF
        self.upf_dynamic  = STATIC_UPF_NODE
        self.upf_static   = STATIC_UPF_NODE

        # Metrics
        self.lat_dynamic  = 0.0
        self.lat_static   = 0.0
        self.eng_dynamic  = 0.0
        self.eng_static   = 0.0
        self.improvement  = 0.0
        self.timestamp    = 0

        # History (for charts)
        self.h_time        = deque(maxlen=HISTORY_LEN)
        self.h_lat_dyn     = deque(maxlen=HISTORY_LEN)
        self.h_lat_stat    = deque(maxlen=HISTORY_LEN)
        self.h_eng_dyn     = deque(maxlen=HISTORY_LEN)
        self.h_eng_stat    = deque(maxlen=HISTORY_LEN)
        self.h_pkt_rate    = deque(maxlen=HISTORY_LEN)
        self.h_improvement = deque(maxlen=HISTORY_LEN)

        self._stop = threading.Event()


STATE = State()


# ─────────────────────────────────────────────────────────────────
# UPF PLACEMENT ALGORITHMS
# ─────────────────────────────────────────────────────────────────
def node_cost(G: nx.Graph, node: int, traffic_load: float) -> float:
    gnb_nodes = [n for n, d in G.nodes(data=True) if d["type"] == "gNB"]
    total_lat = total_eng = 0.0
    for src in gnb_nodes:
        try:
            path = nx.shortest_path(G, source=src, target=node, weight="latency")
            for i in range(len(path) - 1):
                e = G.edges[path[i], path[i + 1]]
                total_lat += e["latency"]
                total_eng += e["energy"]
        except nx.NetworkXNoPath:
            total_lat += 999.0
    return total_lat + total_eng + traffic_load * 0.5


def dynamic_placement(G: nx.Graph, traffic_load: float) -> int:
    candidates = [n for n, d in G.nodes(data=True) if d["type"] in ("MEC", "Core")]
    return min(candidates, key=lambda n: node_cost(G, n, traffic_load))


def compute_metrics(G: nx.Graph, upf_node: int) -> tuple:
    gnb_nodes = [n for n, d in G.nodes(data=True) if d["type"] == "gNB"]
    total_lat = total_eng = 0.0
    for src in gnb_nodes:
        try:
            path = nx.shortest_path(G, source=src, target=upf_node, weight="latency")
            for i in range(len(path) - 1):
                e = G.edges[path[i], path[i + 1]]
                total_lat += e["latency"]
                total_eng += e["energy"]
        except nx.NetworkXNoPath:
            total_lat += 999.0
    return round(total_lat, 2), round(total_eng, 2)


# ─────────────────────────────────────────────────────────────────
# TRAFFIC SOURCE THREADS
# ─────────────────────────────────────────────────────────────────
def detect_interface() -> str:
    """
    FIX: Use `tshark -D` to list available capture interfaces and
    automatically pick the first one that looks like Wi-Fi or Ethernet.
    This is more reliable than guessing the name from IFACE_CANDIDATES
    because on Windows the interface name visible to tshark/pyshark often
    differs from the friendly name shown in Network Settings.

    Returns the tshark interface name (e.g. "\\Device\\NPF_{GUID}") or the
    first candidate from IFACE_CANDIDATES that tshark lists, so pyshark can
    use it directly.
    """
    try:
        # Run tshark -D to enumerate capture-capable interfaces.
        # The output lines look like:
        #   1. \Device\NPF_{GUID} (Wi-Fi)
        #   2. \Device\NPF_{GUID} (Ethernet)
        result = subprocess.run(
            ["tshark", "-D"],
            capture_output=True, text=True, timeout=10
        )
        lines = result.stdout.strip().splitlines()
        preferred = ["wi-fi", "wifi", "wlan", "wireless", "ethernet", "eth"]
        for line in lines:
            lower = line.lower()
            # Pick the first interface whose friendly name matches a preferred keyword
            for kw in preferred:
                if kw in lower:
                    # Extract the interface token (second word after the index)
                    parts = line.split(None, 1)
                    if len(parts) >= 2:
                        iface = parts[1].split(" (")[0].strip()
                        print(f"[INFO] Auto-detected capture interface: {iface} ({line.strip()})")
                        return iface
        # Fallback: return the very first interface tshark found
        if lines:
            parts = lines[0].split(None, 1)
            if len(parts) >= 2:
                iface = parts[1].split(" (")[0].strip()
                print(f"[INFO] No preferred interface found; using first: {iface}")
                return iface
    except FileNotFoundError:
        print("[WARN] tshark not found in PATH. Falling back to candidate list.")
    except Exception as e:
        print(f"[WARN] Interface detection failed ({e}). Falling back to candidate list.")

    # Last resort: try the hard-coded friendly names (works when Wireshark
    # is installed and the names match exactly).
    return IFACE_CANDIDATES[0] if IFACE_CANDIDATES else ""


def try_live_capture() -> str:
    """
    Return the interface name to use for live capture, or '' on failure.
    We no longer do a probe open/close here because that probe itself can
    trigger the asyncio error (it runs in the main thread before a loop
    exists for the background thread).  Instead we just confirm pyshark is
    importable and let detect_interface() find the right adapter.
    """
    try:
        import pyshark  # noqa: F401  – just verify it is installed
    except ImportError:
        print("[WARN] pyshark not installed. Using simulation mode.")
        return ""

    iface = detect_interface()
    if iface:
        print(f"[INFO] Live capture will use interface: {iface}")
    return iface


def live_capture_thread(iface: str):
    # FIX: Windows background threads have no asyncio event loop by default.
    # PyShark uses asyncio internally (via its TSharkCrashException / async
    # packet-reading machinery).  We must create a NEW event loop and make it
    # the "current" loop for this thread BEFORE calling any pyshark API.
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        import pyshark
        cap = pyshark.LiveCapture(interface=iface, bpf_filter="ip")
        count = size = 0
        t0 = time.time()
        for pkt in cap.sniff_continuously():
            if STATE._stop.is_set():
                cap.close()
                break
            count += 1
            try:
                size += int(pkt.length)
            except Exception:
                size += 64
            now = time.time()
            if now - t0 >= 1.0:
                pkt_rate = count / (now - t0)
                avg_sz   = size / max(count, 1)
                with STATE.lock:
                    STATE.packet_rate  = round(pkt_rate, 2)
                    STATE.avg_pkt_size = round(avg_sz, 1)
                    STATE.traffic_load = round(min(pkt_rate / 50.0, 1.0) * 10.0, 2)
                count = size = 0
                t0 = now
    except Exception as e:
        print(f"[WARN] Live capture failed: {e}. Switching to simulation.")
        with STATE.lock:
            STATE.live_capture = False
        simulated_traffic_thread()
    finally:
        # Clean up the event loop we created for this thread.
        loop.close()


def simulated_traffic_thread():
    t = 0
    while not STATE._stop.is_set():
        t += 1
        base  = 5.0 + 3.0 * math.sin(t * 0.18)
        spike = random.uniform(0, 5) if random.random() > 0.82 else 0.0
        rate  = max(0.0, base + spike + random.gauss(0, 0.4))
        with STATE.lock:
            STATE.packet_rate  = round(rate, 2)
            STATE.avg_pkt_size = round(random.uniform(200, 1400), 1)
            STATE.traffic_load = round(min(rate / 20.0, 1.0) * 10.0, 2)
        time.sleep(1.0)


# ─────────────────────────────────────────────────────────────────
# SIMULATION ENGINE THREAD
# ─────────────────────────────────────────────────────────────────
def simulation_engine():
    while not STATE._stop.is_set():
        with STATE.lock:
            tl = STATE.traffic_load
            G  = STATE.G

        # Drift edge weights (network dynamics)
        for u, v in G.edges():
            G.edges[u, v]["latency"] = round(
                max(0.3, G.edges[u, v]["latency"] + random.gauss(0, 0.25)), 2)
            G.edges[u, v]["energy"] = round(
                max(0.1, G.edges[u, v]["energy"]  + random.gauss(0, 0.08)), 2)

        upf_dyn  = dynamic_placement(G, tl)
        upf_stat = STATIC_UPF_NODE

        lat_dyn,  eng_dyn  = compute_metrics(G, upf_dyn)
        lat_stat, eng_stat = compute_metrics(G, upf_stat)

        # Traffic-load penalty (static suffers more)
        lat_dyn  = round(lat_dyn  + tl * 0.25, 2)
        lat_stat = round(lat_stat + tl * 0.80, 2)
        eng_dyn  = round(eng_dyn  + tl * 0.08, 2)
        eng_stat = round(eng_stat + tl * 0.20, 2)

        improvement = round(((lat_stat - lat_dyn) / lat_stat) * 100, 1) if lat_stat > 0 else 0.0

        with STATE.lock:
            STATE.upf_dynamic  = upf_dyn
            STATE.upf_static   = upf_stat
            STATE.lat_dynamic  = lat_dyn
            STATE.lat_static   = lat_stat
            STATE.eng_dynamic  = eng_dyn
            STATE.eng_static   = eng_stat
            STATE.improvement  = improvement
            STATE.timestamp   += 1
            t = STATE.timestamp
            STATE.h_time.append(t)
            STATE.h_lat_dyn.append(lat_dyn)
            STATE.h_lat_stat.append(lat_stat)
            STATE.h_eng_dyn.append(eng_dyn)
            STATE.h_eng_stat.append(eng_stat)
            STATE.h_pkt_rate.append(STATE.packet_rate)
            STATE.h_improvement.append(improvement)

        # ── Console output ────────────────────────────────────────
        mode = "LIVE" if STATE.live_capture else "SIM"
        print(
            f"[t={t:>4}] [{mode}] "
            f"PktRate={STATE.packet_rate:>6.2f} pps  "
            f"TrafficLoad={tl:>5.2f}  "
            f"UPF={upf_dyn} (dyn) / {upf_stat} (stat)  "
            f"Latency={lat_dyn:>6.2f}ms vs {lat_stat:>6.2f}ms  "
            f"Energy={eng_dyn:>5.2f} vs {eng_stat:>5.2f}  "
            f"Improvement={improvement:>+5.1f}%"
        )

        time.sleep(1.0)


# ─────────────────────────────────────────────────────────────────
# MATPLOTLIB DASHBOARD
# ─────────────────────────────────────────────────────────────────
def style_axes(ax, title="", xlabel="Time (s)", ylabel=""):
    ax.set_facecolor(C_PANEL)
    ax.tick_params(colors=C_DIM, labelsize=8)
    for spine in ax.spines.values():
        spine.set_edgecolor(C_BORDER)
    ax.xaxis.label.set_color(C_DIM)
    ax.yaxis.label.set_color(C_DIM)
    ax.set_xlabel(xlabel, fontsize=8)
    ax.set_ylabel(ylabel,  fontsize=8)
    ax.set_title(title, color=C_TEXT, fontsize=9, fontweight="bold", pad=6)
    ax.grid(True, color=C_BORDER, linewidth=0.5, alpha=0.7)


def build_figure():
    plt.rcParams.update({
        "figure.facecolor":  C_BG,
        "text.color":        C_TEXT,
        "font.family":       "monospace",
        "axes.facecolor":    C_PANEL,
    })

    fig = plt.figure(figsize=(17, 9))
    fig.suptitle(
        "Real-Time Dynamic UPF Placement  ─  5G Core Network Monitor",
        color=C_TEXT, fontsize=13, fontweight="bold", y=0.98
    )

    # Layout: left big (network graph) + right 4 charts
    gs = gridspec.GridSpec(4, 2, figure=fig,
                           left=0.04, right=0.97,
                           top=0.94, bottom=0.06,
                           wspace=0.35, hspace=0.55)

    ax_net  = fig.add_subplot(gs[:, 0])          # full-height left
    ax_lat  = fig.add_subplot(gs[0, 1])
    ax_eng  = fig.add_subplot(gs[1, 1])
    ax_pkt  = fig.add_subplot(gs[2, 1])
    ax_imp  = fig.add_subplot(gs[3, 1])

    ax_net.set_facecolor(C_PANEL)
    ax_net.set_title("5G Network Topology  (● = active UPF)", color=C_TEXT, fontsize=9, fontweight="bold")
    for sp in ax_net.spines.values():
        sp.set_edgecolor(C_BORDER)
    ax_net.tick_params(left=False, bottom=False, labelleft=False, labelbottom=False)

    style_axes(ax_lat, "Latency Comparison",  ylabel="Latency (ms)")
    style_axes(ax_eng, "Energy Comparison",    ylabel="Energy (W)")
    style_axes(ax_pkt, "Packet Rate",          ylabel="Packets/s")
    style_axes(ax_imp, "Improvement %",        ylabel="Improvement (%)")

    return fig, ax_net, ax_lat, ax_eng, ax_pkt, ax_imp


def draw_network(ax_net):
    """Redraw the network graph onto ax_net."""
    ax_net.cla()
    ax_net.set_facecolor(C_PANEL)
    ax_net.set_title("5G Network Topology  (● = active UPF)", color=C_TEXT, fontsize=9, fontweight="bold")
    for sp in ax_net.spines.values():
        sp.set_edgecolor(C_BORDER)
    ax_net.tick_params(left=False, bottom=False, labelleft=False, labelbottom=False)

    G = STATE.G
    upf_dyn  = STATE.upf_dynamic
    upf_stat = STATE.upf_static

    # Node colours
    node_colors = []
    node_sizes  = []
    for n in G.nodes():
        ntype = NODE_META[n][0]
        if n == upf_dyn:
            node_colors.append(C_RED)
            node_sizes.append(700)
        elif n == upf_stat and upf_stat != upf_dyn:
            node_colors.append(C_ORANGE)
            node_sizes.append(550)
        else:
            node_colors.append(NODE_COLOURS[ntype])
            node_sizes.append(400)

    # Edge widths / colours by latency
    edge_colors = []
    edge_widths = []
    for u, v in G.edges():
        lat = G.edges[u, v]["latency"]
        if lat < 3:
            edge_colors.append(C_GREEN)
            edge_widths.append(2.0)
        elif lat < 6:
            edge_colors.append(C_BLUE)
            edge_widths.append(1.4)
        else:
            edge_colors.append(C_RED)
            edge_widths.append(1.0)

    nx.draw_networkx(G, pos=POS, ax=ax_net,
                     node_color=node_colors, node_size=node_sizes,
                     edge_color=edge_colors, width=edge_widths,
                     font_size=7, font_color=C_BG, font_weight="bold",
                     with_labels=True)

    # Edge latency labels
    edge_labels = {(u, v): f"{G.edges[u,v]['latency']:.1f}" for u, v in G.edges()}
    nx.draw_networkx_edge_labels(G, pos=POS, ax=ax_net,
                                 edge_labels=edge_labels,
                                 font_size=6, font_color=C_DIM,
                                 bbox=dict(boxstyle="round,pad=0.1",
                                           fc=C_BG, alpha=0.6, ec="none"))

    # Legend
    legend_items = [
        mpatches.Patch(color=C_BLUE,   label="gNB"),
        mpatches.Patch(color=C_GREEN,  label="MEC"),
        mpatches.Patch(color=C_ORANGE, label="Core"),
        mpatches.Patch(color=C_RED,    label=f"Dynamic UPF (node {upf_dyn})"),
    ]
    if upf_stat != upf_dyn:
        legend_items.append(
            mpatches.Patch(color=C_ORANGE, label=f"Static UPF (node {upf_stat})"))
    ax_net.legend(handles=legend_items, loc="lower left",
                  facecolor=C_PANEL, edgecolor=C_BORDER,
                  labelcolor=C_TEXT, fontsize=7)

    # Info box
    mode = "LIVE CAPTURE" if STATE.live_capture else "SIMULATION"
    info = (
        f"Mode : {mode}\n"
        f"PktRate : {STATE.packet_rate:.2f} pps\n"
        f"TrafficLoad : {STATE.traffic_load:.2f}\n"
        f"Latency Δ : {STATE.improvement:+.1f}%"
    )
    ax_net.text(0.98, 0.98, info, transform=ax_net.transAxes,
                va="top", ha="right", fontsize=7.5,
                color=C_TEXT, family="monospace",
                bbox=dict(boxstyle="round,pad=0.5",
                          fc=C_PANEL, ec=C_BORDER, alpha=0.9))


# ─────────────────────────────────────────────────────────────────
# ANIMATION UPDATE
# ─────────────────────────────────────────────────────────────────
def make_updater(fig, ax_net, ax_lat, ax_eng, ax_pkt, ax_imp):
    def _fill(ax, xs, ys1, ys2=None, c1=C_BLUE, c2=C_RED,
              label1="Dynamic", label2="Static"):
        ax.cla()
        style_axes(ax,
                   title=ax.get_title() or "",
                   ylabel=ax.get_ylabel() or "")
        if not xs:
            return
        ax.plot(xs, ys1, color=c1, lw=1.5, label=label1)
        if ys2 is not None:
            ax.plot(xs, ys2, color=c2, lw=1.5, linestyle="--", label=label2)
        ax.legend(fontsize=7, facecolor=C_PANEL,
                  edgecolor=C_BORDER, labelcolor=C_TEXT, loc="upper left")
        ax.relim(); ax.autoscale_view()

    def update(_frame):
        with STATE.lock:
            xs   = list(STATE.h_time)
            ld   = list(STATE.h_lat_dyn)
            ls   = list(STATE.h_lat_stat)
            ed   = list(STATE.h_eng_dyn)
            es   = list(STATE.h_eng_stat)
            pr   = list(STATE.h_pkt_rate)
            imp  = list(STATE.h_improvement)

        # ── Network graph ───────────────────────────────────────
        draw_network(ax_net)

        # ── Latency ─────────────────────────────────────────────
        ax_lat.cla()
        style_axes(ax_lat, "Latency Comparison", ylabel="Latency (ms)")
        if xs:
            ax_lat.plot(xs, ld, color=C_BLUE,   lw=1.5, label="Dynamic")
            ax_lat.plot(xs, ls, color=C_RED,    lw=1.5, linestyle="--", label="Static")
            ax_lat.legend(fontsize=7, facecolor=C_PANEL,
                          edgecolor=C_BORDER, labelcolor=C_TEXT)
            ax_lat.relim(); ax_lat.autoscale_view()

        # ── Energy ──────────────────────────────────────────────
        ax_eng.cla()
        style_axes(ax_eng, "Energy Comparison", ylabel="Energy (W)")
        if xs:
            ax_eng.plot(xs, ed, color=C_GREEN,  lw=1.5, label="Dynamic")
            ax_eng.plot(xs, es, color=C_ORANGE, lw=1.5, linestyle="--", label="Static")
            ax_eng.legend(fontsize=7, facecolor=C_PANEL,
                          edgecolor=C_BORDER, labelcolor=C_TEXT)
            ax_eng.relim(); ax_eng.autoscale_view()

        # ── Packet Rate ─────────────────────────────────────────
        ax_pkt.cla()
        style_axes(ax_pkt, "Packet Rate", ylabel="Packets/s")
        if xs:
            ax_pkt.fill_between(xs, pr, alpha=0.3, color=C_PURPLE)
            ax_pkt.plot(xs, pr, color=C_PURPLE, lw=1.5)
            ax_pkt.relim(); ax_pkt.autoscale_view()

        # ── Improvement % ───────────────────────────────────────
        ax_imp.cla()
        style_axes(ax_imp, "Improvement %", ylabel="Improvement (%)")
        if xs:
            colors = [C_GREEN if v >= 0 else C_RED for v in imp]
            ax_imp.bar(xs, imp, color=colors, width=0.8, alpha=0.8)
            ax_imp.axhline(0, color=C_DIM, lw=0.8, linestyle="--")
            ax_imp.relim(); ax_imp.autoscale_view()

        return []

    return update


# ─────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────
def main():
    print("=" * 70)
    print("  Real-Time Dynamic UPF Placement  –  5G Core Network Monitor")
    print("=" * 70)
    print("  Starting … press Ctrl+C or close the window to exit.\n")

    # ── Start traffic source ─────────────────────────────────────
    iface = try_live_capture()
    if iface:
        STATE.live_capture = True
        t_traffic = threading.Thread(target=live_capture_thread,
                                     args=(iface,), daemon=True)
    else:
        print("[INFO] Using simulated traffic.\n")
        STATE.live_capture = False
        t_traffic = threading.Thread(target=simulated_traffic_thread, daemon=True)

    t_traffic.start()

    # ── Start simulation engine ──────────────────────────────────
    t_engine = threading.Thread(target=simulation_engine, daemon=True)
    t_engine.start()

    # ── Build + run the dashboard ────────────────────────────────
    try:
        fig, ax_net, ax_lat, ax_eng, ax_pkt, ax_imp = build_figure()
        update_fn = make_updater(fig, ax_net, ax_lat, ax_eng, ax_pkt, ax_imp)

        ani = FuncAnimation(fig, update_fn,
                            interval=UPDATE_INTERVAL_MS,
                            blit=False, cache_frame_data=False)

        print("[INFO] Graph window opened. Data updates every second.")
        plt.show()

    except KeyboardInterrupt:
        pass
    finally:
        STATE._stop.set()
        print("\n[INFO] Shutting down …")


if __name__ == "__main__":
    main()

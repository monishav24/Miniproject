#!/usr/bin/env python3
"""
advanced_5g_anim.py
===================
Generates a highly realistic, professional HD (1920x1080) presentation video (MP4)
visualizing a 5G Core Network with dynamic UPF placement.
Features:
 - Reads topology natively from topology_predictive.json if available.
 - 100 mobile users (eMBB, mMTC, URLLC) moving via random walk.
 - Realistic Cloud/Server icons for UPFs.
 - Smartphone/IoT/Vehicle icons for Users.
 - Real-time animated traffic packets color-coded by load/latency.
 - On-screen HUD dashboard with 4 real-time metrics.
 - Outputs to 5G_simulation.mp4
"""

import math, random, os, json, urllib.request
import numpy as np
import networkx as nx

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patheffects as pe
from matplotlib.animation import FuncAnimation
from matplotlib.offsetbox import OffsetImage, AnnotationBbox
import matplotlib.gridspec as gridspec
from PIL import Image

np.random.seed(102)
random.seed(102)

# ─────────────────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────────────────
N_NODES = 30
N_USERS = 100
FRAMES  = 600   # 25 seconds at 24 fps

BG_COLOR    = "#0a1128"
EDGE_IDLE   = "#1f3a5f"
METRICS_BG  = "#040b17"
TEXT_COLOR  = "#e0eaf5"

# ─────────────────────────────────────────────────────────
# ICONS DOWNLOAD (Fallback handled)
# ─────────────────────────────────────────────────────────
ICONS = {
    "upf":     "https://cdn-icons-png.flaticon.com/512/3208/3208082.png",   # Server/Cloud
    "eMBB":    "https://cdn-icons-png.flaticon.com/512/644/644458.png",     # Smartphone
    "mMTC":    "https://cdn-icons-png.flaticon.com/512/1183/1183674.png",   # IoT Sensor
    "URLLC":   "https://cdn-icons-png.flaticon.com/512/3204/3204121.png",   # Autonomous Vehicle
    "router":  "https://cdn-icons-png.flaticon.com/512/3067/3067260.png",   # Generic network node
}

os.makedirs("icons", exist_ok=True)
images_cache = {}

print("Downloading/Loading realistic icons...")
for name, url in ICONS.items():
    filepath = f"icons/{name}.png"
    if not os.path.exists(filepath):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req) as resp, open(filepath, 'wb') as f:
                f.write(resp.read())
        except Exception as e:
            pass
    try:
        img = Image.open(filepath).convert("RGBA")
        img.thumbnail((120, 120), Image.Resampling.LANCZOS)
        images_cache[name] = np.array(img)
    except Exception:
        images_cache[name] = None

def draw_icon(ax, x, y, name, zoom=0.15, alpha=1.0):
    img = images_cache.get(name)
    if img is not None:
        im = OffsetImage(img, zoom=zoom, alpha=alpha)
        ab = AnnotationBbox(im, (x, y), frameon=False, pad=0.0)
        ax.add_artist(ab)
        return True
    return False

# ─────────────────────────────────────────────────────────
# NETWORK TOPOLOGY (Reads JSON from main.py if exists)
# ─────────────────────────────────────────────────────────
G = nx.Graph()
POS = {}

if os.path.exists("topology_predictive.json"):
    print("Loading topology from topology_predictive.json...")
    with open("topology_predictive.json", "r") as f:
        data = json.load(f)
    for n_data in data.get("nodes", []):
        G.add_node(int(n_data["id"]))
    for e_data in data.get("edges", data.get("links", [])):
        G.add_edge(int(e_data["source"]), int(e_data["target"]))
    N_NODES = len(G.nodes)
else:
    print("JSON not found. Generating default topology...")
    G = nx.barabasi_albert_graph(N_NODES, 2, seed=42)

# Verify connectivity
if not nx.is_connected(G):
    cc = list(nx.connected_components(G))[0]
    G = G.subgraph(cc).copy()
    N_NODES = len(G.nodes)

# Professional layout
pos_raw = nx.kamada_kawai_layout(G)
xs = np.array([pos_raw[i][0] for i in list(G.nodes)])
ys = np.array([pos_raw[i][1] for i in list(G.nodes)])
xs = 10 + 80 * (xs - xs.min()) / (xs.max() - xs.min())
ys = 15 + 75 * (ys - ys.min()) / (ys.max() - ys.min())

for idx, n in enumerate(list(G.nodes)):
    POS[n] = (xs[idx], ys[idx])

# Determine UPFs
bc = nx.betweenness_centrality(G)
sorted_nodes = sorted(bc, key=bc.get, reverse=True)
STATIC_UPFS = sorted_nodes[:5]
DYNAMIC_UPFS = sorted_nodes[2:7]

# ─────────────────────────────────────────────────────────
# USERS & MOBILITY
# ─────────────────────────────────────────────────────────
user_types = ["eMBB"] * int(N_USERS * 0.5) + ["mMTC"] * int(N_USERS * 0.35) + ["URLLC"] * int(N_USERS * 0.15)
random.shuffle(user_types)
node_list = list(G.nodes)

class User:
    def __init__(self, uid, ttype):
        self.uid = uid
        self.node = random.choice(node_list)
        self.ttype = ttype
        self.offset_x = random.uniform(-2.5, 2.5)
        self.offset_y = random.uniform(-2.5, 2.5)
        self.target_offset_x = self.offset_x
        self.target_offset_y = self.offset_y

    def walk(self):
        # Move across macro network via random walk
        if random.random() < 0.18:
            nbrs = list(G.neighbors(self.node))
            if nbrs:
                self.node = random.choice(nbrs)
        
        # Adjust micro position
        if random.random() < 0.1:
            self.target_offset_x = random.uniform(-3.5, 3.5)
            self.target_offset_y = random.uniform(-3.5, 3.5)
        
        self.offset_x += (self.target_offset_x - self.offset_x) * 0.15
        self.offset_y += (self.target_offset_y - self.offset_y) * 0.15

USERS = [User(i, user_types[i]) for i in range(N_USERS)]

# ─────────────────────────────────────────────────────────
# PACKETS & TRAFFIC
# ─────────────────────────────────────────────────────────
class Packet:
    def __init__(self, src, dst, color):
        self.src = src
        self.dst = dst
        self.t = 0.0
        self.speed = random.uniform(0.02, 0.06)
        self.color = color

    def step(self):
        self.t += self.speed
        return self.t >= 1.0

    def get_pos(self):
        x0, y0 = POS[self.src]
        x1, y1 = POS[self.dst]
        return x0 + (x1-x0)*self.t, y0 + (y1-y0)*self.t

packets = []

def spawn_packets(upf_list, congested=False):
    for u in USERS:
        if random.random() < 0.10:
            assigned_upf = min(upf_list, key=lambda x: nx.shortest_path_length(G, u.node, x))
            if u.node != assigned_upf:
                if congested and u.ttype == "eMBB":
                    col = "#ff3300" 
                elif congested:
                    col = "#ff9900"
                else:
                    col = "#00ffaa" if u.ttype == "URLLC" else "#00aaff"
                    
                path = nx.shortest_path(G, u.node, assigned_upf)
                if len(path) > 1:
                    packets.append(Packet(path[0], path[1], col))

# ─────────────────────────────────────────────────────────
# METRICS TRACKING
# ─────────────────────────────────────────────────────────
hist_lat = []
hist_eng = []
hist_sla = []
hist_rec = []

def update_metrics(frame):
    # Simulate realistic main.py changes over time
    if frame < FRAMES // 2:
        # Static Phase - Congestion increasing
        penalty = frame / (FRAMES / 2)
        lat = 30 + 45 * penalty + random.uniform(-3, 3)
        eng = 450 + 80 * penalty + random.uniform(-10, 10)
        sla = 5 + 35 * penalty + random.uniform(-2, 2)
        rec = 0
    else:
        # Predictive Phase - Optimized immediately after reconfiguration
        recovery_time = max(0.0, 1.0 - (frame - FRAMES // 2) / 45.0)
        lat = 18 + 57 * recovery_time + random.uniform(-2, 2)
        eng = 340 + 190 * recovery_time + random.uniform(-5, 5)
        sla = 2 + 38 * recovery_time + random.uniform(0, 1)
        rec = 4 if frame == FRAMES // 2 else 0
        if len(hist_rec) > 0:
            rec = hist_rec[-1] + rec

    hist_lat.append(max(5, lat))
    hist_eng.append(max(200, eng))
    hist_sla.append(max(0, sla))
    if len(hist_rec) == 0:
        hist_rec.append(0)
    elif frame != FRAMES // 2:
        hist_rec.append(hist_rec[-1])

# ─────────────────────────────────────────────────────────
# ANIMATION RENDERING SETUP (1920x1080)
# ─────────────────────────────────────────────────────────
# 16x9 inches at 120 DPI = 1920x1080 resolution
fig = plt.figure(figsize=(16, 9), dpi=120, facecolor=BG_COLOR)
gs = gridspec.GridSpec(5, 5, figure=fig, left=0.02, right=0.98, top=0.98, bottom=0.02, wspace=0.3)

ax_net = fig.add_subplot(gs[:, 0:4])
ax_net.set_facecolor(BG_COLOR)
ax_net.axis("off")

ax_dash = fig.add_subplot(gs[:, 4])
ax_dash.set_facecolor(METRICS_BG)
ax_dash.axis("off")

def update(frame):
    global packets
    ax_net.clear()
    ax_net.axis("off")
    ax_net.set_xlim(-5, 105)
    ax_net.set_ylim(-5, 105)

    mode = "STATIC PLACEMENT" if frame < FRAMES // 2 else "PREDICTIVE PLACEMENT"
    current_upfs = STATIC_UPFS if frame < FRAMES // 2 else DYNAMIC_UPFS
    congested = (frame > FRAMES // 5 and frame < FRAMES // 2)

    if frame % 3 == 0:
        for u in USERS:
            u.walk()
            
    update_metrics(frame)
    spawn_packets(current_upfs, congested)
    
    packets = [p for p in packets if not p.step()]

    # Draw Edges Grid
    for u, v in G.edges():
        ax_net.plot([POS[u][0], POS[v][0]], [POS[u][1], POS[v][1]], color=EDGE_IDLE, lw=0.6, alpha=0.5, zorder=1)

    # Draw Nodes (Routers vs UPFs)
    for n in G.nodes():
        x, y = POS[n]
        if n in current_upfs:
            g_col = "#ff3333" if mode == "STATIC PLACEMENT" else "#00ffcc"
            ax_net.scatter(x, y, s=800, color=g_col, alpha=0.15 + 0.1*math.sin(frame*0.1), zorder=2)
            if not draw_icon(ax_net, x, y, "upf", zoom=0.08):
                ax_net.scatter(x, y, marker="s", s=180, color=g_col, zorder=3)
        else:
            if not draw_icon(ax_net, x, y, "router", zoom=0.04, alpha=0.6):
                ax_net.scatter(x, y, s=50, color="#225588", zorder=3)

    # Draw Users
    for u in USERS:
        x, y = POS[u.node]
        ux = x + u.offset_x
        uy = y + u.offset_y
        z = 0.035 if u.ttype == "eMBB" else 0.045
        if not draw_icon(ax_net, ux, uy, u.ttype, zoom=z):
            col = "#ffff00" if u.ttype == "URLLC" else "#ff00ff"
            ax_net.scatter(ux, uy, s=35, color=col, zorder=4)

    # Draw Packets
    if packets:
        px = [p.get_pos()[0] for p in packets]
        py = [p.get_pos()[1] for p in packets]
        pc = [p.color for p in packets]
        ax_net.scatter(px, py, s=18, c=pc, zorder=5)

    # Title & Mode Indicator
    ax_net.text(50, 102, "Predictive Dynamic UPF Placement in 5G Core Networks", 
                 color=TEXT_COLOR, fontsize=15, ha='center', fontweight='bold',
                 path_effects=[pe.withStroke(linewidth=3, foreground=BG_COLOR)])
    
    m_color = "#ff4444" if mode == "STATIC PLACEMENT" and congested else "#00ffaa"
    ax_net.text(50, -2, f"CURRENT MODE: {mode}", color=m_color, fontsize=12, ha='center', fontweight='bold',
                 bbox=dict(facecolor='#0d2040', edgecolor=m_color, boxstyle='round,pad=0.5'))

    # Draw Dashboard Panel
    ax_dash.clear()
    ax_dash.axis("off")
    ax_dash.set_xlim(0, 10)
    ax_dash.set_ylim(0, 100)
    
    ax_dash.text(5, 95, "REAL-TIME DASHBOARD", color="#00ffcc", fontsize=11, ha="center", fontweight="bold")
    
    c_lat, c_eng, c_sla, c_rec = hist_lat[-1], hist_eng[-1], hist_sla[-1], hist_rec[-1]

    def draw_gauge(y, label, val, unit, color):
        ax_dash.text(1, y, label, color=TEXT_COLOR, fontsize=9, fontweight="bold")
        ax_dash.text(9, y, f"{val:.1f} {unit}", color=color, fontsize=12, ha="right", fontweight="bold")
        ax_dash.plot([1, 9], [y-2.5, y-2.5], color="#112244", lw=6, solid_capstyle="round")
        pct = min(1.0, val / (100 if "ms" in unit or "%" in unit else 1000))
        ax_dash.plot([1, 1 + 8*pct], [y-2.5, y-2.5], color=color, lw=6, solid_capstyle="round")

    draw_gauge(85, "Average Latency", c_lat, "ms", "#ff4444" if c_lat > 50 else "#00ffaa")
    draw_gauge(70, "Energy Consumption", c_eng, "W", "#ffaa00" if c_eng > 400 else "#00aaff")
    draw_gauge(55, "SLA Violations", c_sla, "%", "#ff4444" if c_sla > 15 else "#00ffaa")
    
    ax_dash.text(5, 40, "Total Reconfigurations", color=TEXT_COLOR, fontsize=9, ha="center", fontweight="bold")
    ax_dash.text(5, 34, f"{c_rec}", color="#ff00ff", fontsize=18, ha="center", fontweight="bold")

    # Draw Legend
    ax_dash.text(5, 20, "LEGEND", color="#00ffcc", fontsize=10, ha="center", fontweight="bold")
    loc_y = 15
    for lbl, icon in [("UPF Server / Cloud", "upf"), ("Network Router", "router"),
                      ("Smartphone (eMBB)", "eMBB"), ("IoT Sensor (mMTC)", "mMTC"), 
                      ("Vehicle (URLLC)", "URLLC")]:
        ax_dash.text(3, loc_y, lbl, color=TEXT_COLOR, fontsize=8, va="center")
        draw_icon(ax_dash, 1.5, loc_y, icon, zoom=0.035)
        loc_y -= 3.5

print("Rendering HD MP4 Video... (takes several minutes)")
anim = FuncAnimation(fig, update, frames=FRAMES, interval=41) # ~24fps

import shutil
import warnings
warnings.filterwarnings("ignore")

try:
    if shutil.which("ffmpeg"):
        anim.save("5G_simulation.mp4", writer="ffmpeg", fps=24, dpi=120)
        print("✓ Successfully created 5G_simulation.mp4")
    else:
        print("⚠️ ffmpeg not installed on this system! Falling back to GIF generation.")
        anim.save("5G_simulation.gif", writer="pillow", fps=15)
        print("✓ Successfully saved 5G_simulation.gif (Fallback)")
except Exception as e:
    print(f"❌ Error saving animation: {e}")

#!/usr/bin/env python3
"""
advanced_5g_anim.py
===================
Generates a highly realistic, professional 2D presentation video (MP4)
visualizing a 5G Core Network with dynamic UPF placement.
Features:
 - 30 nodes, 56 edges, 100 mobile users (eMBB, mMTC, URLLC).
 - Cloud/Server icons for UPFs.
 - Smartphone/IoT/Vehicle icons for Users.
 - Real-time animated traffic packets color-coded by load/latency.
 - On-screen HUD dashboard with 4 real-time metrics.
"""

import math, random, os, urllib.request
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

np.random.seed(101)
random.seed(101)

# ─────────────────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────────────────
N_NODES = 30
N_EDGES = 56
N_USERS = 100
FRAMES  = 600

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
            print(f"Warning: Could not download {name} icon -> {e}")
    try:
        img = Image.open(filepath).convert("RGBA")
        # Pre-scale images slightly to save memory during animation
        img.thumbnail((100, 100), Image.Resampling.LANCZOS)
        images_cache[name] = np.array(img)
    except Exception:
        images_cache[name] = None

# Custom wrapper to draw icons
def draw_icon(ax, x, y, name, zoom=0.15, alpha=1.0):
    img = images_cache.get(name)
    if img is not None:
        im = OffsetImage(img, zoom=zoom, alpha=alpha)
        ab = AnnotationBbox(im, (x, y), frameon=False, pad=0.0)
        ax.add_artist(ab)
        return True
    return False

# ─────────────────────────────────────────────────────────
# NETWORK TOPOLOGY (30 Nodes, ~56 Edges)
# ─────────────────────────────────────────────────────────
# A connected graph with exactly 56 edges
G = nx.gnm_random_graph(N_NODES, N_EDGES, seed=42)
while not nx.is_connected(G):
    G = nx.gnm_random_graph(N_NODES, N_EDGES)

# Professional hierarchical-ish layout
pos_raw = nx.kamada_kawai_layout(G)
xs = np.array([pos_raw[i][0] for i in range(N_NODES)])
ys = np.array([pos_raw[i][1] for i in range(N_NODES)])
xs = 10 + 80 * (xs - xs.min()) / (xs.max() - xs.min())
ys = 15 + 75 * (ys - ys.min()) / (ys.max() - ys.min())
POS = {i: (xs[i], ys[i]) for i in range(N_NODES)}

# Determine initial static UPFs and later dynamic (Predictive) UPFs
bc = nx.betweenness_centrality(G)
sorted_nodes = sorted(bc, key=bc.get, reverse=True)
STATIC_UPFS = sorted_nodes[:5]
DYNAMIC_UPFS = sorted_nodes[2:7]

# ─────────────────────────────────────────────────────────
# USERS (eMBB, mMTC, URLLC)
# ─────────────────────────────────────────────────────────
user_types = ["eMBB"]*50 + ["mMTC"]*35 + ["URLLC"]*15
random.shuffle(user_types)

class User:
    def __init__(self, uid, ttype):
        self.uid = uid
        self.node = random.randint(0, N_NODES - 1)
        self.ttype = ttype
        self.offset_x = random.uniform(-2.5, 2.5)
        self.offset_y = random.uniform(-2.5, 2.5)
        
        # Jitter targets for smooth movement within a node cluster
        self.target_offset_x = self.offset_x
        self.target_offset_y = self.offset_y

    def walk(self):
        # Move across macro network
        if random.random() < 0.2:
            nbrs = list(G.neighbors(self.node))
            if nbrs:
                self.node = random.choice(nbrs)
        # Update micro jitter
        if random.random() < 0.1:
            self.target_offset_x = random.uniform(-3.0, 3.0)
            self.target_offset_y = random.uniform(-3.0, 3.0)
        
        # Smooth ease towards offset
        self.offset_x += (self.target_offset_x - self.offset_x) * 0.2
        self.offset_y += (self.target_offset_y - self.offset_y) * 0.2

USERS = [User(i, user_types[i]) for i in range(N_USERS)]

# ─────────────────────────────────────────────────────────
# PACKETS & TRAFFIC
# ─────────────────────────────────────────────────────────
class Packet:
    def __init__(self, src, dst, color):
        self.src = src
        self.dst = dst
        self.t = 0.0
        self.speed = random.uniform(0.02, 0.05)
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
        if random.random() < 0.15:  # 15% chance to send a packet this frame
            upf = min(upf_list, key=lambda x: nx.shortest_path_length(G, u.node, x))
            if u.node != upf:
                # Color based on latency (congested implies red/orange)
                if congested and u.ttype == "eMBB":
                    col = "#ff3300"
                elif congested:
                    col = "#ffaa00"
                else:
                    col = "#00ffaa" if u.ttype == "URLLC" else "#00aaff"
                    
                path = nx.shortest_path(G, u.node, upf)
                if len(path) > 1:
                    packets.append(Packet(path[0], path[1], col))

# ─────────────────────────────────────────────────────────
# METRICS TRACKING
# ─────────────────────────────────────────────────────────
hist_latency = []
hist_energy = []
hist_sla = []
hist_reconfig = []

def compute_metrics(upfs, frame):
    # Base dummy logic evolving over time
    if frame < FRAMES // 2: # Static phase (getting congested)
        penalty = min(1.0, frame / (FRAMES/2))
        lat = 30 + 50 * penalty + random.uniform(-5, 5)
        eng = 450 + 100 * penalty + random.uniform(-10, 10)
        sla = 5 + 25 * penalty + random.uniform(-2, 2)
        reconf = 0
    else: # Dynamic phase (optimized)
        recovery = max(0.0, 1.0 - (frame - FRAMES/2) / 60.0) # Drops quickly
        lat = 15 + 65 * recovery + random.uniform(-2, 2)
        eng = 320 + 230 * recovery + random.uniform(-5, 5)
        sla = 1 + 29 * recovery + random.uniform(0, 2)
        reconf = 4 if frame == FRAMES//2 else 0
        if len(hist_reconfig) > 0:
            reconf = hist_reconfig[-1] + reconf

    hist_latency.append(max(5, lat))
    hist_energy.append(max(200, eng))
    hist_sla.append(max(0, sla))
    if len(hist_reconfig) == 0:
        hist_reconfig.append(0)
    elif frame != FRAMES//2:
        hist_reconfig.append(hist_reconfig[-1])

# ─────────────────────────────────────────────────────────
# ANIMATION SETUP
# ─────────────────────────────────────────────────────────
fig = plt.figure(figsize=(16, 9), facecolor=BG_COLOR, dpi=120)
gs = gridspec.GridSpec(5, 5, figure=fig, left=0.02, right=0.98, top=0.98, bottom=0.02, wspace=0.3, hspace=0.3)

ax_main = fig.add_subplot(gs[:, 0:4])
ax_main.set_facecolor(BG_COLOR)
ax_main.axis("off")

# Dashboard on the right
ax_dash = fig.add_subplot(gs[:, 4])
ax_dash.set_facecolor(METRICS_BG)
ax_dash.axis("off")

# Pre-draw edge lines
edge_lines = []
for u, v in G.edges():
    line, = ax_main.plot([POS[u][0], POS[v][0]], [POS[u][1], POS[v][1]], color=EDGE_IDLE, lw=0.8, alpha=0.5, zorder=1)
    edge_lines.append(line)

# Node scatter for glow
node_scats = ax_main.scatter([], [], s=80, color="#1e4a7a", zorder=2, alpha=0.4)

def update(frame):
    global packets
    ax_main.clear()
    ax_main.axis("off")
    ax_main.set_xlim(-5, 105)
    ax_main.set_ylim(-5, 105)

    phase = "STATIC" if frame < FRAMES // 2 else "PREDICTIVE (DYNAMIC)"
    current_upfs = STATIC_UPFS if frame < FRAMES // 2 else DYNAMIC_UPFS
    congested = (frame > FRAMES // 4 and frame < FRAMES // 2)

    # 1. Update Mobility & Packets
    if frame % 3 == 0:
        for u in USERS:
            u.walk()
            
    compute_metrics(current_upfs, frame)
    spawn_packets(current_upfs, congested)
    
    # Prune & step packets
    active_packets = []
    for p in packets:
        if not p.step():
            active_packets.append(p)
    packets = active_packets

    # 2. Draw Edges
    for u, v in G.edges():
        ax_main.plot([POS[u][0], POS[v][0]], [POS[u][1], POS[v][1]], color=EDGE_IDLE, lw=0.8, alpha=0.5, zorder=1)

    # 3. Draw Nodes (UPFs vs Routers)
    for n in range(N_NODES):
        x, y = POS[n]
        if n in current_upfs:
            ax_main.scatter(x, y, s=600, color="#1188ff" if phase=="STATIC" else "#00ffcc", alpha=0.2 + 0.1*math.sin(frame*0.2), zorder=2)
            if not draw_icon(ax_main, x, y, "upf", zoom=0.08):
                ax_main.scatter(x, y, marker="s", s=150, color="#00ffff", zorder=3)
        else:
            if not draw_icon(ax_main, x, y, "router", zoom=0.04, alpha=0.6):
                ax_main.scatter(x, y, s=40, color="#336699", zorder=3)

    # 4. Draw Users
    for u in USERS:
        x, y = POS[u.node]
        ux = x + u.offset_x
        uy = y + u.offset_y
        z = 0.03
        if u.ttype == "URLLC": z = 0.04
        if not draw_icon(ax_main, ux, uy, u.ttype, zoom=z):
            col = "#ffff00" if u.ttype == "URLLC" else "#ff00ff"
            ax_main.scatter(ux, uy, s=30, color=col, zorder=4)

    # 5. Draw Packets
    px_list = [p.get_pos()[0] for p in packets]
    py_list = [p.get_pos()[1] for p in packets]
    pc_list = [p.color for p in packets]
    if px_list:
        ax_main.scatter(px_list, py_list, s=15, c=pc_list, zorder=5)

    # 6. Title and Labels
    ax_main.text(50, 102, "Predictive Multi-UPF Placement in 5G Core Networks", 
                 color=TEXT_COLOR, fontsize=14, ha='center', fontweight='bold')
    
    mode_color = "#ff4444" if phase=="STATIC" and congested else "#00ffaa"
    ax_main.text(50, -2, f"MODE: {phase}", color=mode_color, fontsize=12, ha='center', fontweight='bold',
                 bbox=dict(facecolor='#0d2040', edgecolor=mode_color, boxstyle='round,pad=0.5'))

    # 7. Update Dashboard
    ax_dash.clear()
    ax_dash.axis("off")
    ax_dash.set_xlim(0, 10)
    ax_dash.set_ylim(0, 100)
    
    ax_dash.text(5, 95, "REAL-TIME METRICS", color="#00ffcc", fontsize=11, ha="center", fontweight="bold")
    
    # Current values
    c_lat = hist_latency[-1]
    c_eng = hist_energy[-1]
    c_sla = hist_sla[-1]
    c_rec = hist_reconfig[-1]

    def draw_gauge(y, label, val, unit, color):
        ax_dash.text(1, y, label, color=TEXT_COLOR, fontsize=9, fontweight="bold")
        ax_dash.text(9, y, f"{val:.1f} {unit}", color=color, fontsize=12, ha="right", fontweight="bold")
        # Base bar
        ax_dash.plot([1, 9], [y-2.5, y-2.5], color="#112244", lw=6, solid_capstyle="round")
        # Fill bar
        pct = min(1.0, val / (100 if "ms" in unit or "%" in unit else 1000))
        ax_dash.plot([1, 1 + 8*pct], [y-2.5, y-2.5], color=color, lw=6, solid_capstyle="round")

    col_lat = "#ff4444" if c_lat > 50 else "#00ffaa"
    col_sla = "#ff4444" if c_sla > 15 else "#00ffaa"
    col_eng = "#ffaa00" if c_eng > 400 else "#00aaff"

    draw_gauge(85, "Average Latency", c_lat, "ms", col_lat)
    draw_gauge(70, "Energy Consumption", c_eng, "W", col_eng)
    draw_gauge(55, "SLA Violations", c_sla, "%", col_sla)
    
    ax_dash.text(5, 40, "Reconfigurations", color=TEXT_COLOR, fontsize=9, ha="center", fontweight="bold")
    ax_dash.text(5, 34, f"{c_rec}", color="#ff00ff", fontsize=18, ha="center", fontweight="bold")

    # Legend
    ax_dash.text(5, 20, "LEGEND", color="#00ffcc", fontsize=10, ha="center", fontweight="bold")
    leg_y = 15
    for lbl, img in [("UPF Server", "upf"), ("Smartphone (eMBB)", "eMBB"), 
                     ("IoT Sensor (mMTC)", "mMTC"), ("Vehicle (URLLC)", "URLLC")]:
        ax_dash.text(3, leg_y, lbl, color=TEXT_COLOR, fontsize=8, va="center")
        draw_icon(ax_dash, 1.5, leg_y, img, zoom=0.04)
        leg_y -= 4

print("Starting Animation Render... (This may take several minutes)")
anim = FuncAnimation(fig, update, frames=FRAMES, interval=50)

# Save as MP4
try:
    print("Saving MP4 video using ffmpeg...")
    anim.save("5g_core_presentation.mp4", writer="ffmpeg", fps=24, dpi=120)
    print("✓ Successfully saved 5g_core_presentation.mp4")
except Exception as e:
    print(f"Failed to save MP4: {e}. Attempting GIF fallback...")
    try:
        anim.save("5g_core_presentation.gif", writer="pillow", fps=15)
        print("✓ Successfully saved 5g_core_presentation.gif")
    except Exception as e2:
        print("Failed to save all animations.")

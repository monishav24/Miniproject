#!/usr/bin/env python3
"""
animate_5g_upf.py
=================
High-quality animated visualization of a 5G core network demonstrating
predictive and dynamic UPF placement.

Run:
    python animate_5g_upf.py

Outputs:
    - 5g_upf_snapshot.png  (always saved)
    - 5g_upf_animation.gif (if pillow is installed)
    - 5g_upf_animation.mp4 (if ffmpeg is installed)
"""

import math
import random
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.patheffects as pe
from matplotlib.animation import FuncAnimation
from matplotlib.lines import Line2D
import matplotlib.gridspec as gridspec
import networkx as nx

random.seed(42)
np.random.seed(42)

# ─────────────────────────────────────────────────────────
# COLOUR PALETTE
# ─────────────────────────────────────────────────────────
BG        = "#060b1a"
EDGE_COL  = "#1a3a5c"
GOOD_PATH = "#00ff99"
BAD_PATH  = "#ff6600"
GRID_COL  = "#0d1f3c"
ACCENT    = "#88aaff"
TEXT_COL  = "#c8e6ff"
METRIC_OK = "#00ffaa"
METRIC_BAD= "#ff4455"
TRAFFIC_COL = {'eMBB': '#00aaff', 'URLLC': '#ffdd00', 'mMTC': '#bb88ff'}

# ─────────────────────────────────────────────────────────
# NETWORK TOPOLOGY
# ─────────────────────────────────────────────────────────
N_NODES = 30
G = nx.barabasi_albert_graph(N_NODES, 2, seed=7)
pos_raw = nx.spring_layout(G, seed=42, k=0.55)

xs = np.array([pos_raw[i][0] for i in range(N_NODES)])
ys = np.array([pos_raw[i][1] for i in range(N_NODES)])
xs_range = float(np.max(xs) - np.min(xs)) or 1.0
ys_range = float(np.max(ys) - np.min(ys)) or 1.0
xs = 5.0 + 90.0 * (xs - xs.min()) / xs_range
ys = 5.0 + 90.0 * (ys - ys.min()) / ys_range
POS = {i: (float(xs[i]), float(ys[i])) for i in range(N_NODES)}

BC = nx.betweenness_centrality(G, weight=None)
top_nodes    = sorted(BC, key=BC.get, reverse=True)
STATIC_UPFS  = top_nodes[:5]
PRED_UPFS    = top_nodes[1:6]   # slightly shifted for predictive demo

# ─────────────────────────────────────────────────────────
# USERS
# ─────────────────────────────────────────────────────────
N_USERS = 20
TRAFFIC_TYPES = ['eMBB', 'URLLC', 'mMTC']

class UserSim:
    def __init__(self, uid):
        self.uid   = uid
        self.node  = random.randint(0, N_NODES - 1)
        self.ttype = random.choice(TRAFFIC_TYPES)

    def walk(self):
        nbrs = list(G.neighbors(self.node))
        if nbrs and random.random() < 0.5:
            self.node = random.choice(nbrs)

USERS = [UserSim(i) for i in range(N_USERS)]

# ─────────────────────────────────────────────────────────
# PARTICLES
# ─────────────────────────────────────────────────────────
class Particle:
    def __init__(self, src, dst, color=GOOD_PATH):
        self.src   = src
        self.dst   = dst
        self.t     = 0.0
        self.speed = random.uniform(0.04, 0.09)
        self.color = color
        self.done  = False

    def step(self):
        self.t = min(1.0, self.t + self.speed)
        if self.t >= 1.0:
            self.done = True

    def bezier(self, t_val):
        x0, y0 = POS[self.src]
        x1, y1 = POS[self.dst]
        mx = (x0 + x1) / 2 + (y1 - y0) * 0.15
        my = (y0 + y1) / 2 - (x1 - x0) * 0.15
        bx = (1 - t_val)**2 * x0 + 2 * (1 - t_val) * t_val * mx + t_val**2 * x1
        by = (1 - t_val)**2 * y0 + 2 * (1 - t_val) * t_val * my + t_val**2 * y1
        return bx, by

    def head(self):
        return self.bezier(self.t)

# ─────────────────────────────────────────────────────────
# METRICS
# ─────────────────────────────────────────────────────────
def metric_curve(n, base, amplitude, noise=0.15, seed=0):
    rng = np.random.RandomState(seed)
    t   = np.linspace(0, 4 * np.pi, n)
    return base + amplitude * np.sin(t) + rng.randn(n) * noise * amplitude

N_FRAMES_PER_SCENE = 120
TOTAL_FRAMES       = N_FRAMES_PER_SCENE * 4

latency_static = metric_curve(TOTAL_FRAMES, 45, 18, seed=1)
latency_pred   = metric_curve(TOTAL_FRAMES, 28, 10, seed=2)
energy_static  = metric_curve(TOTAL_FRAMES, 300, 80, seed=3)
energy_pred    = metric_curve(TOTAL_FRAMES, 215, 45, seed=4)
sla_static     = np.clip(metric_curve(TOTAL_FRAMES, 18, 10, seed=5), 0, None).astype(int)
sla_pred       = np.clip(metric_curve(TOTAL_FRAMES,  7,  5, seed=6), 0, None).astype(int)

# ─────────────────────────────────────────────────────────
# FIGURE SETUP
# ─────────────────────────────────────────────────────────
fig = plt.figure(figsize=(16, 9), facecolor=BG)
gs  = gridspec.GridSpec(
    3, 4, figure=fig,
    left=0.01, right=0.99, top=0.97, bottom=0.03,
    wspace=0.40, hspace=0.55,
)

ax_net = fig.add_subplot(gs[:, :3])
ax_lat = fig.add_subplot(gs[0, 3])
ax_eng = fig.add_subplot(gs[1, 3])
ax_sla = fig.add_subplot(gs[2, 3])

for ax in [ax_net, ax_lat, ax_eng, ax_sla]:
    ax.set_facecolor(BG)
    for spine in ax.spines.values():
        spine.set_color(EDGE_COL)

ax_net.set_xlim(-2, 102)
ax_net.set_ylim(-2, 102)
ax_net.set_aspect('equal')
ax_net.axis('off')

def style_metric_ax(ax, title):
    ax.set_facecolor("#080e20")
    ax.tick_params(colors=ACCENT, labelsize=7)
    ax.set_title(title, color=ACCENT, fontsize=8, pad=4, fontweight='bold')
    for spine in ax.spines.values():
        spine.set_color(EDGE_COL)
    ax.grid(True, color=GRID_COL, linewidth=0.5)

style_metric_ax(ax_lat, "Latency (ms)")
style_metric_ax(ax_eng, "Energy (units)")
style_metric_ax(ax_sla, "SLA Violations")

# ─────────────────────────────────────────────────────────
# DRAW HELPERS
# ─────────────────────────────────────────────────────────
def draw_edges(ax, upfs):
    upf_set = set(upfs)
    for u, v in G.edges():
        xu, yu = POS[u]
        xv, yv = POS[v]
        near = u in upf_set or v in upf_set
        ax.plot([xu, xv], [yu, yv],
                color="#1e4a7a" if near else EDGE_COL,
                lw=1.0 if near else 0.4,
                alpha=0.7, zorder=1)


def draw_nodes(ax, upfs, frame):
    draw_edges(ax, upfs)
    upf_set = set(upfs)

    # User scatter blobs (layered for glow)
    for u in USERS:
        x, y = POS[u.node]
        c = TRAFFIC_COL[u.ttype]
        ax.scatter(x, y, s=120, color=c, alpha=0.12, zorder=2)
        ax.scatter(x, y, s=55,  color=c, alpha=0.35, zorder=3)
        ax.scatter(x, y, s=18,  color=c, alpha=0.95, zorder=4)

    # UPF scatter blobs
    pulse = 0.5 + 0.3 * math.sin(frame * 0.2)
    for n in range(N_NODES):
        if n not in upf_set:
            continue
        x, y = POS[n]
        ax.scatter(x, y, s=500 * pulse, color="#ff4444", alpha=0.10, zorder=5)
        ax.scatter(x, y, s=200,         color="#ff4444", alpha=0.28, zorder=6)
        ax.scatter(x, y, s=90,          color="#ff4444", alpha=1.00, zorder=7)
        ax.text(x, y + 3.2, 'UPF', color='white', fontsize=5.5,
                ha='center', va='bottom', fontweight='bold', zorder=8)


def draw_particles(ax, parts):
    for p in parts:
        if p.done:
            continue
        bx, by = p.head()
        ax.scatter(bx, by, s=24, color=p.color, alpha=0.95, zorder=9)
        for frac in [0.88, 0.74, 0.60]:
            t2     = p.t * frac
            bx2, by2 = p.bezier(t2)
            ax.scatter(bx2, by2, s=8, color=p.color, alpha=0.25, zorder=8)


def overlay_text(ax, lines, y_start=28, dy=5.5, fontsize=9):
    for i, (txt, col, bold) in enumerate(lines):
        t = ax.text(
            1, y_start - i * dy, txt,
            color=col, fontsize=fontsize, ha='left', va='top',
            fontweight='bold' if bold else 'normal', zorder=20,
            transform=ax.transData,
        )
        t.set_path_effects([pe.withStroke(linewidth=2.5, foreground=BG)])


def metric_readout(ax, lat, eng, sla, static_mode):
    lat_c = METRIC_OK if lat < 35 else METRIC_BAD
    sla_c = METRIC_OK if sla < 10 else METRIC_BAD
    mode_label = "STATIC" if static_mode else "PREDICTIVE"
    mode_col   = "#ff9944" if static_mode else METRIC_OK
    ax.text(100, 100, f"Mode: {mode_label}", color=mode_col,
            fontsize=8, ha='right', va='top', fontweight='bold', zorder=20,
            transform=ax.transData)
    ax.text(100, 94,  f"Latency : {lat:.1f} ms", color=lat_c,
            fontsize=8, ha='right', va='top', zorder=20, transform=ax.transData)
    ax.text(100, 88,  f"Energy  : {eng:.0f} u",  color=METRIC_OK,
            fontsize=8, ha='right', va='top', zorder=20, transform=ax.transData)
    ax.text(100, 82,  f"SLA viol: {sla}",         color=sla_c,
            fontsize=8, ha='right', va='top', zorder=20, transform=ax.transData)


def update_metric_chart(ax, y_s, y_p, frame, label):
    ax.clear()
    style_metric_ax(ax, label)
    n = min(frame + 1, len(y_s))
    xs_plot = list(range(n))
    ax.plot(xs_plot, list(y_s[:n]), color="#ff6644", lw=1.2, label='Static')
    ax.plot(xs_plot, list(y_p[:n]), color=METRIC_OK,  lw=1.2, label='Predictive')
    if n > 0:
        ax.set_xlim(0, TOTAL_FRAMES)
        ax.set_ylim(
            min(float(y_p.min()), float(y_s.min())) * 0.85,
            float(y_s.max()) * 1.10,
        )
    ax.legend(fontsize=5.5, loc='upper right',
              facecolor="#0a1428", edgecolor=EDGE_COL, labelcolor=TEXT_COL)


def draw_legend(ax):
    handles = [
        mpatches.Patch(color='#00aaff', label='User (eMBB)'),
        mpatches.Patch(color='#ffdd00', label='User (URLLC)'),
        mpatches.Patch(color='#bb88ff', label='User (mMTC)'),
        mpatches.Patch(color='#ff4444', label='UPF node'),
        Line2D([0], [0], color=GOOD_PATH, lw=2, label='Efficient path'),
        Line2D([0], [0], color=BAD_PATH,  lw=2, label='Congested path'),
    ]
    ax.legend(handles=handles, loc='lower left', fontsize=6,
              facecolor="#080e20", edgecolor=EDGE_COL,
              labelcolor=TEXT_COL, ncol=2, framealpha=0.85)


# ─────────────────────────────────────────────────────────
# SCENES
# ─────────────────────────────────────────────────────────
SCENES = [
    # (start_frame, banner, subtitle, overlay_lines, upf_list, congested, static_mode)
    (
        0,
        "Scene 1: Network Topology & User Mobility",
        "30-node Barabási–Albert topology  ·  3 traffic types",
        [
            ("User Mobility", ACCENT, True),
            ("Users roam the network over time", TEXT_COL, False),
            ("eMBB · URLLC · mMTC traffic types", '#aaddff', False),
        ],
        STATIC_UPFS, False, True,
    ),
    (
        N_FRAMES_PER_SCENE,
        "Scene 2: Traffic Demand Increases — Static UPF Placement",
        "Fixed UPFs cannot adapt  →  congestion builds",
        [
            ("Traffic Demand Increasing", '#ffaa44', True),
            ("Static UPFs cause congestion", METRIC_BAD, False),
            ("Latency ↑   SLA violations ↑", METRIC_BAD, False),
        ],
        STATIC_UPFS, True, True,
    ),
    (
        N_FRAMES_PER_SCENE * 2,
        "Scene 3: Predicting Future Traffic Load",
        "Moving-average model forecasts user movement",
        [
            ("Predicted Load", '#ffdd44', True),
            ("Intelligent forecast in progress …", ACCENT, False),
            ("UPF repositioning decision computed", ACCENT, False),
        ],
        STATIC_UPFS, False, True,
    ),
    (
        N_FRAMES_PER_SCENE * 3,
        "Scene 4: Dynamic Predictive UPF Placement — QoS Optimised",
        "UPFs reposition  →  latency drops  ·  SLA violations minimised",
        [
            ("Dynamic UPF Placement", METRIC_OK, True),
            ("Latency ↓   Energy ↓   SLA violations ↓", METRIC_OK, False),
            ("Predictive placement outperforms static", METRIC_OK, False),
        ],
        PRED_UPFS, False, False,
    ),
]


def get_scene(frame):
    current = SCENES[0]
    for sc in SCENES:
        if frame >= sc[0]:
            current = sc
    return current


# particle pool
scene_particles: list = []


def animate(frame):
    global scene_particles

    ax_net.clear()
    ax_net.set_xlim(-2, 102)
    ax_net.set_ylim(-2, 102)
    ax_net.set_aspect('equal')
    ax_net.axis('off')
    ax_net.set_facecolor(BG)

    sc_start, banner, subtitle, overlay, upfs, congested, static_mode = get_scene(frame)

    # Mobility
    if frame % 8 == 0:
        for u in USERS:
            u.walk()

    # Particles
    if frame % 6 == 0:
        for _ in range(5):
            src_user = random.choice(USERS)
            dst_upf  = random.choice(upfs)
            col      = BAD_PATH if congested else GOOD_PATH
            scene_particles.append(Particle(src_user.node, dst_upf, col))
    for p in scene_particles:
        p.step()
    scene_particles = [p for p in scene_particles if not p.done]

    draw_nodes(ax_net, upfs, frame)
    draw_particles(ax_net, scene_particles)
    overlay_text(ax_net, overlay)
    draw_legend(ax_net)

    # Metrics readout
    fi = min(frame, TOTAL_FRAMES - 1)
    lat = float(latency_static[fi]) if static_mode else float(latency_pred[fi])
    eng = float(energy_static[fi])  if static_mode else float(energy_pred[fi])
    sla = int(sla_static[fi])       if static_mode else int(sla_pred[fi])
    metric_readout(ax_net, lat, eng, sla, static_mode)

    # Title
    ax_net.text(50, 101.5,
                "Predictive Multi-UPF Dynamic Placement — 5G Core Network",
                color=TEXT_COL, fontsize=10, ha='center', va='bottom',
                fontweight='bold', zorder=20, transform=ax_net.transData)
    ax_net.text(50, 99.2, subtitle, color=ACCENT, fontsize=7.5,
                ha='center', va='bottom', zorder=20, transform=ax_net.transData)

    # Scene banner
    ax_net.text(50, -1.5, banner, color='white', fontsize=8.5,
                ha='center', va='top', fontweight='bold',
                bbox=dict(facecolor='#0d2040', edgecolor=EDGE_COL,
                          boxstyle='round,pad=0.4', alpha=0.9),
                zorder=21, transform=ax_net.transData)

    # Side charts
    update_metric_chart(ax_lat, latency_static, latency_pred, fi, "Latency (ms)")
    update_metric_chart(ax_eng, energy_static,  energy_pred,  fi, "Energy (units)")
    update_metric_chart(ax_sla, sla_static,     sla_pred,     fi, "SLA Violations")

    return []


# ─────────────────────────────────────────────────────────
# RENDER
# ─────────────────────────────────────────────────────────
print("Rendering animation …  (this may take ~20-30 seconds)")

anim = FuncAnimation(fig, animate, frames=TOTAL_FRAMES,
                     interval=60, blit=False, repeat=False)

# Snapshot (always works)
plt.savefig("5g_upf_snapshot.png", facecolor=BG, dpi=150, bbox_inches='tight')
print("  [✓] Snapshot → 5g_upf_snapshot.png")

# GIF (needs pillow)
try:
    anim.save("5g_upf_animation.gif", writer='pillow', fps=15,
              savefig_kwargs=dict(facecolor=BG))
    print("  [✓] GIF     → 5g_upf_animation.gif")
except Exception as e:
    print(f"  GIF skipped ({e})")

# MP4 (needs ffmpeg)
try:
    anim.save("5g_upf_animation.mp4", writer='ffmpeg', fps=20, dpi=120,
              savefig_kwargs=dict(facecolor=BG))
    print("  [✓] MP4     → 5g_upf_animation.mp4")
except Exception as e:
    print(f"  MP4 skipped ({e})")

plt.show()

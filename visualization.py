"""
visualization.py
Generates matplotlib comparison plots and auto-opens them.
Produces 4 separate PNG files:
  - latency_comparison.png
  - energy_comparison.png
  - sla_violation_comparison.png
  - cost_trend.png
"""
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend for headless/WSL
import matplotlib.pyplot as plt
import subprocess
import sys
import os

from cost_function import calculate_cost


def _save_and_show(fig, filename):
    """Saves to PNG and attempts to open the image."""
    fig.savefig(filename, dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f"  [✓] Saved → {filename}")


def plot_all(metrics_dict, output_dir="."):
    """
    Generates 4 comparison plots from a dict of algorithm metrics.
    metrics_dict = { 'AlgoName': {'latency': [...], 'energy': [...], 'sla': [...]} }
    """
    algos = list(metrics_dict.keys())
    time_steps = len(metrics_dict[algos[0]]['latency'])
    x = range(time_steps)

    # ---- 1. Latency Comparison ----
    fig, ax = plt.subplots(figsize=(10, 5))
    for algo in algos:
        ax.plot(x, metrics_dict[algo]['latency'], label=algo, linewidth=1.2)
    ax.set_title('Average Latency over Time', fontsize=14, fontweight='bold')
    ax.set_xlabel('Time Step')
    ax.set_ylabel('Latency (ms)')
    ax.legend()
    ax.grid(True, alpha=0.3)
    _save_and_show(fig, os.path.join(output_dir, "latency_comparison.png"))

    # ---- 2. Energy Comparison ----
    fig, ax = plt.subplots(figsize=(10, 5))
    for algo in algos:
        ax.plot(x, metrics_dict[algo]['energy'], label=algo, linewidth=1.2)
    ax.set_title('Energy Consumption over Time', fontsize=14, fontweight='bold')
    ax.set_xlabel('Time Step')
    ax.set_ylabel('Energy (Units)')
    ax.legend()
    ax.grid(True, alpha=0.3)
    _save_and_show(fig, os.path.join(output_dir, "energy_comparison.png"))

    # ---- 3. SLA Violations ----
    fig, ax = plt.subplots(figsize=(10, 5))
    for algo in algos:
        ax.plot(x, metrics_dict[algo]['sla'], label=algo, linewidth=1.2)
    ax.set_title('SLA Violations over Time', fontsize=14, fontweight='bold')
    ax.set_xlabel('Time Step')
    ax.set_ylabel('Violations')
    ax.legend()
    ax.grid(True, alpha=0.3)
    _save_and_show(fig, os.path.join(output_dir, "sla_violation_comparison.png"))

    # ---- 4. Cost Trend ----
    fig, ax = plt.subplots(figsize=(10, 5))
    for algo in algos:
        costs = [
            calculate_cost(l, e, s)
            for l, e, s in zip(
                metrics_dict[algo]['latency'],
                metrics_dict[algo]['energy'],
                metrics_dict[algo]['sla'],
            )
        ]
        ax.plot(x, costs, label=algo, linewidth=1.2)
    ax.set_title('Total Operational Cost (C = αL + βE + γ·SLA)', fontsize=14,
                 fontweight='bold')
    ax.set_xlabel('Time Step')
    ax.set_ylabel('Cost')
    ax.legend()
    ax.grid(True, alpha=0.3)
    _save_and_show(fig, os.path.join(output_dir, "cost_trend.png"))

    print("  [✓] All 4 comparison graphs generated.")


def open_graphs(output_dir="."):
    """Try to open the generated PNGs using the system viewer."""
    images = [
        "latency_comparison.png",
        "energy_comparison.png",
        "sla_violation_comparison.png",
        "cost_trend.png",
    ]
    for img in images:
        path = os.path.join(output_dir, img)
        if os.path.exists(path):
            try:
                if sys.platform == "win32":
                    os.startfile(path)
                elif sys.platform == "darwin":
                    subprocess.Popen(["open", path])
                else:
                    # Linux / WSL – try xdg-open, suppress errors
                    subprocess.Popen(["xdg-open", path],
                                     stdout=subprocess.DEVNULL,
                                     stderr=subprocess.DEVNULL)
            except Exception:
                pass  # Viewer not available – graphs are still saved

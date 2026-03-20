#!/usr/bin/env python3
"""
main.py — One-Command Orchestrator
====================================
Runs the ENTIRE pipeline with a single command:

    python3 main.py

Steps executed automatically:
  1. Python simulation   (all 5 placement algorithms, 200 time steps)
  2. Export topology.json (for Static & Predictive modes)
  3. Execute ns-3         (cd ~/ns-3-dev && ./ns3 run scratch/upf-sim)
  4. Generate NetAnim XML (static.xml, predictive.xml)
  5. Launch NetAnim       (~/ns-3-dev/netanim/NetAnim)
  6. Parse flowmon.xml
  7. Generate matplotlib graphs
  8. Open graphs automatically

Environment:
  - Windows WSL (Ubuntu)
  - ns-3 installed at ~/ns-3-dev
  - NetAnim at ~/ns-3-dev/netanim
"""

import os
import sys
import json
import shutil
import subprocess
import time

from network_model import create_network, export_topology
from traffic_model import generate_users
from mobility_model import random_walk
from prediction_model import Predictor
from placement_algorithms import (
    static_placement,
    random_placement,
    greedy_placement,
    predictive_placement,
    QLearningPlacement,
)
from evaluation import evaluate_placement
from cost_function import calculate_cost
import visualization

# ───────────────────────────────────────────────────────────
# CONFIGURATION
# ───────────────────────────────────────────────────────────
NUM_NODES   = 30
NUM_USERS   = 100
NUM_UPFS    = 5
TIME_STEPS  = 200

NS3_DIR     = os.path.expanduser("~/ns-3-dev")
NETANIM_BIN = os.path.join(NS3_DIR, "netanim", "NetAnim")
SCRATCH_SRC = os.path.join(NS3_DIR, "scratch", "upf-sim.cc")

# Where this project lives (auto-detected)
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))


# ───────────────────────────────────────────────────────────
# STEP 1: Run Python Simulation
# ───────────────────────────────────────────────────────────
def run_simulation():
    """Runs all 5 placement algorithms over TIME_STEPS and collects metrics."""
    print("=" * 60)
    print("  STEP 1: Running Python Placement Simulation")
    print("=" * 60)

    G = create_network(NUM_NODES)
    users = generate_users(G, NUM_USERS)
    predictor = Predictor()
    ql_agent = QLearningPlacement(NUM_NODES, NUM_UPFS)

    algorithms = ['Static', 'Random', 'Greedy', 'Predictive', 'Q-Learning']
    metrics = {
        algo: {'latency': [], 'energy': [], 'sla': [], 'reconfigs': 0}
        for algo in algorithms
    }

    # Static placement — computed once
    static_upfs = static_placement(G, NUM_UPFS)
    last_upfs = {algo: [] for algo in algorithms}
    last_upfs['Static'] = list(static_upfs)
    ql_current = list(static_upfs)  # Q-learning starts from static

    for t in range(TIME_STEPS):
        random_walk(users, G)
        predictor.update(users)
        predictions = predictor.predict_next_nodes()

        upfs = {
            'Static':     static_upfs,
            'Random':     random_placement(G, NUM_UPFS),
            'Greedy':     greedy_placement(G, users, NUM_UPFS),
            'Predictive': predictive_placement(G, predictions, NUM_UPFS),
        }

        # Q-Learning action
        ql_action = ql_agent.get_placement(ql_current)
        upfs['Q-Learning'] = ql_action

        for algo in algorithms:
            if t > 0 and set(upfs[algo]) != set(last_upfs[algo]):
                metrics[algo]['reconfigs'] += 1
            last_upfs[algo] = list(upfs[algo])

            lat, eng, sla = evaluate_placement(G, users, upfs[algo])
            metrics[algo]['latency'].append(lat)
            metrics[algo]['energy'].append(eng)
            metrics[algo]['sla'].append(sla)

        # Q-Learning reward = negative cost (we want to minimize)
        ql_lat, ql_eng, ql_sla = (
            metrics['Q-Learning']['latency'][-1],
            metrics['Q-Learning']['energy'][-1],
            metrics['Q-Learning']['sla'][-1],
        )
        reward = -calculate_cost(ql_lat, ql_eng, ql_sla)
        ql_agent.update(ql_current, ql_action, reward)
        ql_current = ql_action

    print(f"  [✓] Simulation complete ({TIME_STEPS} steps, {len(algorithms)} algorithms)")
    return G, users, upfs, metrics


# ───────────────────────────────────────────────────────────
# STEP 2: Export Topology JSON
# ───────────────────────────────────────────────────────────
def export_topologies(G, users, upfs):
    """Exports Static and Predictive topologies to JSON."""
    print("\n" + "=" * 60)
    print("  STEP 2: Exporting Topology JSON files")
    print("=" * 60)

    export_topology(G, upfs['Static'], users, "topology_static.json")
    export_topology(G, upfs['Predictive'], users, "topology_predictive.json")


# ───────────────────────────────────────────────────────────
# STEP 3 & 4: Execute ns-3 and generate animation XML
# ───────────────────────────────────────────────────────────
def copy_ns3_scratch():
    """Copies upf-sim.cc to the ns-3 scratch directory."""
    local_cc = os.path.join(PROJECT_DIR, "scratch", "upf-sim.cc")
    if not os.path.exists(local_cc):
        print("  [!] scratch/upf-sim.cc not found in project — skipping ns-3.")
        return False
    if not os.path.isdir(NS3_DIR):
        print(f"  [!] ns-3 directory not found at {NS3_DIR} — skipping ns-3.")
        return False

    os.makedirs(os.path.join(NS3_DIR, "scratch"), exist_ok=True)
    shutil.copy2(local_cc, SCRATCH_SRC)
    print(f"  [✓] Copied upf-sim.cc → {SCRATCH_SRC}")
    return True


def run_ns3(mode):
    """
    Runs ns-3 for a given mode (static / predictive).
    Copies the matching topology JSON to ~/ns-3-dev/topology.json,
    then runs ./ns3 run scratch/upf-sim.
    """
    json_src = os.path.join(PROJECT_DIR, f"topology_{mode}.json")
    json_dst = os.path.join(NS3_DIR, "topology.json")
    shutil.copy2(json_src, json_dst)

    print(f"  Running ns-3 for {mode.upper()} mode ...")
    try:
        result = subprocess.run(
            ["./ns3", "run", "scratch/upf-sim"],
            cwd=NS3_DIR,
            capture_output=True,
            text=True,
            timeout=120,
        )
        if result.returncode == 0:
            print(f"  [✓] ns-3 {mode} simulation completed successfully.")
        else:
            print(f"  [!] ns-3 returned code {result.returncode}")
            if result.stderr:
                # Print only the last few lines to keep output clean
                for line in result.stderr.strip().split('\n')[-5:]:
                    print(f"      {line}")
    except FileNotFoundError:
        print("  [!] ./ns3 not found. Make sure ns-3 is installed at ~/ns-3-dev")
        return False
    except subprocess.TimeoutExpired:
        print("  [!] ns-3 simulation timed out (120s).")
        return False

    # Move outputs to project directory with mode-specific names
    for src_name, dst_name in [
        ("flowmon.xml", f"flowmon_{mode}.xml"),
        ("upf-animation.xml", f"{mode}.xml"),
    ]:
        src = os.path.join(NS3_DIR, src_name)
        dst = os.path.join(PROJECT_DIR, dst_name)
        if os.path.exists(src):
            shutil.move(src, dst)
            print(f"  [✓] {src_name} → {dst_name}")

    return True


def execute_ns3():
    """Full ns-3 pipeline: copy scratch, run Static, run Predictive."""
    print("\n" + "=" * 60)
    print("  STEP 3 & 4: ns-3 Simulation + NetAnim XML Generation")
    print("=" * 60)

    if not copy_ns3_scratch():
        print("  [SKIP] ns-3 simulation skipped (ns-3 not found).")
        print("         Python-only results are still valid.")
        return False

    ok_static = run_ns3("static")
    ok_predict = run_ns3("predictive")
    return ok_static or ok_predict


# ───────────────────────────────────────────────────────────
# STEP 5: Launch NetAnim
# ───────────────────────────────────────────────────────────
def launch_netanim():
    """Attempts to launch NetAnim with the predictive animation file."""
    print("\n" + "=" * 60)
    print("  STEP 5: Launching NetAnim")
    print("=" * 60)

    anim_file = os.path.join(PROJECT_DIR, "predictive.xml")
    if not os.path.exists(anim_file):
        anim_file = os.path.join(PROJECT_DIR, "static.xml")
    if not os.path.exists(anim_file):
        print("  [SKIP] No animation XML found — NetAnim not launched.")
        return

    if not os.path.exists(NETANIM_BIN):
        print(f"  [SKIP] NetAnim binary not found at {NETANIM_BIN}")
        return

    try:
        subprocess.Popen(
            [NETANIM_BIN, anim_file],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        print(f"  [✓] NetAnim launched with {os.path.basename(anim_file)}")
    except Exception as e:
        print(f"  [!] Could not launch NetAnim: {e}")


# ───────────────────────────────────────────────────────────
# STEP 6: Parse flowmon.xml (basic summary)
# ───────────────────────────────────────────────────────────
def parse_flowmon(mode):
    """Extracts basic statistics from flowmon XML if available."""
    path = os.path.join(PROJECT_DIR, f"flowmon_{mode}.xml")
    if not os.path.exists(path):
        return None

    try:
        import xml.etree.ElementTree as ET
        tree = ET.parse(path)
        root = tree.getroot()
        flows = root.findall('.//FlowStats/Flow')
        total_delay = 0.0
        total_pkts = 0
        total_lost = 0
        for flow in flows:
            delay = float(flow.get('delaySum', '0').replace('ns', '')) / 1e6  # to ms
            rx = int(flow.get('rxPackets', '0'))
            lost = int(flow.get('lostPackets', '0'))
            total_delay += delay
            total_pkts += rx
            total_lost += lost
        avg_delay = total_delay / max(1, len(flows))
        return {
            'flows': len(flows),
            'avg_delay_ms': round(avg_delay, 3),
            'total_rx': total_pkts,
            'total_lost': total_lost,
        }
    except Exception as e:
        print(f"  [!] Could not parse {path}: {e}")
        return None


# ───────────────────────────────────────────────────────────
# STEP 7 & 8: Generate and open graphs
# ───────────────────────────────────────────────────────────
def generate_graphs(metrics):
    """Calls visualization module to create and open comparison PNGs."""
    print("\n" + "=" * 60)
    print("  STEP 7 & 8: Generating Comparison Graphs")
    print("=" * 60)

    visualization.plot_all(metrics, output_dir=PROJECT_DIR)
    visualization.open_graphs(output_dir=PROJECT_DIR)


# ───────────────────────────────────────────────────────────
# Console Summary
# ───────────────────────────────────────────────────────────
def print_summary(metrics):
    """Prints a formatted console summary table and improvement stats."""
    print("\n" + "=" * 60)
    print("  PERFORMANCE SUMMARY")
    print("=" * 60)

    header = f"{'Algorithm':<14} {'Avg Lat(ms)':>12} {'Avg Energy':>12} {'Avg SLA V':>10} {'Reconfigs':>10}"
    print(header)
    print("-" * len(header))

    for algo, data in metrics.items():
        n = len(data['latency'])
        avg_l = sum(data['latency']) / n
        avg_e = sum(data['energy']) / n
        avg_s = sum(data['sla']) / n
        rc = data['reconfigs']
        print(f"{algo:<14} {avg_l:>12.2f} {avg_e:>12.2f} {avg_s:>10.2f} {rc:>10}")

    # Improvement: Predictive vs Static
    sl = sum(metrics['Static']['latency'])
    pl = sum(metrics['Predictive']['latency'])
    lat_improv = ((sl - pl) / sl * 100) if sl > 0 else 0

    ss = sum(metrics['Static']['sla'])
    ps = sum(metrics['Predictive']['sla'])
    sla_improv = ((ss - ps) / ss * 100) if ss > 0 else 0

    se = sum(metrics['Static']['energy'])
    pe = sum(metrics['Predictive']['energy'])
    eng_improv = ((se - pe) / se * 100) if se > 0 else 0

    print("\n" + "-" * 50)
    print("  PREDICTIVE vs STATIC  Improvements")
    print("-" * 50)
    print(f"  Latency       : {lat_improv:>+.2f}%")
    print(f"  Energy        : {eng_improv:>+.2f}%")
    print(f"  SLA Violations: {sla_improv:>+.2f}%")
    print(f"  Static  Total SLA Violations : {ss}")
    print(f"  Predictive Total SLA Violations : {ps}")
    print("-" * 50)

    # ns-3 flowmon comparison if available
    fm_static = parse_flowmon("static")
    fm_pred = parse_flowmon("predictive")
    if fm_static or fm_pred:
        print("\n  ns-3 FlowMonitor Results:")
        for label, fm in [("Static", fm_static), ("Predictive", fm_pred)]:
            if fm:
                print(f"    {label}: {fm['flows']} flows, "
                      f"avg delay={fm['avg_delay_ms']}ms, "
                      f"rxPkts={fm['total_rx']}, lost={fm['total_lost']}")


# ───────────────────────────────────────────────────────────
# MAIN ENTRY POINT
# ───────────────────────────────────────────────────────────
def main():
    print()
    print("╔══════════════════════════════════════════════════════════╗")
    print("║  Predictive Multi-UPF Dynamic Placement in 5G Core     ║")
    print("║  Latency- & Energy-Aware with QoS & Mobility Support   ║")
    print("╚══════════════════════════════════════════════════════════╝")
    print(f"  Nodes={NUM_NODES}  Users={NUM_USERS}  UPFs={NUM_UPFS}  Steps={TIME_STEPS}")
    print()

    # Step 1
    G, users, upfs, metrics = run_simulation()

    # Step 2
    export_topologies(G, users, upfs)

    # Steps 3 & 4
    ns3_ok = execute_ns3()

    # Step 5
    if ns3_ok:
        launch_netanim()

    # Step 6 (parsed inside print_summary)

    # Steps 7 & 8
    generate_graphs(metrics)

    # Console summary
    print_summary(metrics)

    print("\n  ✅ Pipeline complete. All outputs saved in project directory.")
    print()


if __name__ == "__main__":
    main()

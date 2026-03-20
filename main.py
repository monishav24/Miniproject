import json
import os
from network_model import create_network
from traffic_model import generate_users
from mobility_model import random_walk
from prediction_model import Predictor
from placement_algorithms import static_placement, random_placement, greedy_placement, predictive_placement
from evaluation import evaluate_placement
import visualization

def main():
    TIME_STEPS = 200
    NUM_NODES = 30
    NUM_USERS = 100
    NUM_UPFS = 5

    print(f"Initializing simulation with {NUM_NODES} nodes, {NUM_USERS} users, {NUM_UPFS} UPFs for {TIME_STEPS} time steps.")
    G = create_network(NUM_NODES)
    users = generate_users(G, NUM_USERS)
    predictor = Predictor()

    algorithms = ['Static', 'Random', 'Greedy', 'Predictive']
    metrics = {algo: {'latency': [], 'energy': [], 'sla': [], 'reconfigs': 0} for algo in algorithms}

    # Static placement is calculated once
    static_upfs = static_placement(G, NUM_UPFS)
    last_upfs = {algo: [] for algo in algorithms}
    last_upfs['Static'] = static_upfs

    for t in range(TIME_STEPS):
        random_walk(users, G)
        predictor.update(users)
        
        # Determine UPFs
        upfs = {}
        upfs['Static'] = static_upfs
        upfs['Random'] = random_placement(G, NUM_UPFS)
        upfs['Greedy'] = greedy_placement(G, users, NUM_UPFS)
        
        predictions = predictor.predict_next_nodes()
        upfs['Predictive'] = predictive_placement(G, predictions, NUM_UPFS)
        
        for algo in algorithms:
            # Check for reconfigurations (UPF switching)
            if t > 0 and set(upfs[algo]) != set(last_upfs[algo]):
                metrics[algo]['reconfigs'] += 1
            last_upfs[algo] = upfs[algo]
            
            l, e, s = evaluate_placement(G, users, upfs[algo])
            metrics[algo]['latency'].append(l)
            metrics[algo]['energy'].append(e)
            metrics[algo]['sla'].append(s)

    # Save visualization
    visualization.plot_metrics(metrics, 'python_metrics.png')
    print("Metrics plotted and saved to python_metrics.png")

    # Calculate SLA before and after
    static_sla = sum(metrics['Static']['sla'])
    predictive_sla = sum(metrics['Predictive']['sla'])
    static_lat = sum(metrics['Static']['latency'])
    predictive_lat = sum(metrics['Predictive']['latency'])

    lat_improvement = ((static_lat - predictive_lat) / static_lat) * 100 if static_lat > 0 else 0

    print("\n--- PERFORMANCE HIGHLIGHTS ---")
    print(f"Latency Improvement (Predictive over Static): {lat_improvement:.2f}%")
    print(f"Total SLA Violations - Static: {static_sla} | Predictive: {predictive_sla}")
    print("--------------------------------\n")

    # Export topology and most recent UPFs to JSON for NS-3
    nodes_data = [{"id": n, "x": G.nodes[n]['pos'][0], "y": G.nodes[n]['pos'][1]} for n in G.nodes()]
    edges_data = [{"source": u, "target": v, "weight": d['weight']} for u, v, d in G.edges(data=True)]
    
    topology_static = {
        "nodes": nodes_data,
        "edges": edges_data,
        "upfs": upfs['Static'],
        "users": [{"id": u.user_id, "node": u.current_node} for u in users]
    }
    
    topology_predictive = {
        "nodes": nodes_data,
        "edges": edges_data,
        "upfs": upfs['Predictive'],
        "users": [{"id": u.user_id, "node": u.current_node} for u in users]
    }

    with open('topology_static.json', 'w') as f:
        json.dump(topology_static, f, indent=4)
        
    with open('topology_predictive.json', 'w') as f:
        json.dump(topology_predictive, f, indent=4)

    print("Exported JSON topologies for ns-3.")
    
    for algo in algorithms:
        avg_l = sum(metrics[algo]['latency'])/TIME_STEPS
        avg_e = sum(metrics[algo]['energy'])/TIME_STEPS
        avg_s = sum(metrics[algo]['sla'])/TIME_STEPS
        print(f"Algorithm: {algo:10} | Avg Latency: {avg_l:.2f} | Avg Energy: {avg_e:.2f} | Avg SLA Vol: {avg_s:.2f} | Reconfigs: {metrics[algo]['reconfigs']}")

if __name__ == "__main__":
    main()

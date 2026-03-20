"""
network_model.py
Creates a Barabási–Albert graph to represent the 5G core network topology.
Exports topology to JSON for ns-3 consumption.
"""
import networkx as nx
import random
import json
import math


def create_network(num_nodes=30, m=2):
    """
    Creates a Barabási–Albert graph with weighted edges.
    Each node is assigned a grid-style (x, y) position for clear NetAnim layout.
    """
    G = nx.barabasi_albert_graph(num_nodes, m, seed=42)

    # Assign weights (representing base propagation delay in ms)
    for u, v in G.edges():
        G[u][v]['weight'] = random.randint(1, 10)

    # Assign grid layout positions for visual clarity
    cols = int(math.ceil(math.sqrt(num_nodes)))
    for i in G.nodes():
        row = i // cols
        col = i % cols
        G.nodes[i]['x'] = float(col * 20)
        G.nodes[i]['y'] = float(row * 20)

    return G


def export_topology(G, upfs, users, filename="topology.json"):
    """
    Exports the graph, UPF list, and user locations to a JSON file
    that the ns-3 C++ script can parse.
    """
    nodes_data = []
    for n in G.nodes():
        nodes_data.append({
            "id": int(n),
            "x": G.nodes[n]['x'],
            "y": G.nodes[n]['y']
        })

    edges_data = []
    for u, v, d in G.edges(data=True):
        edges_data.append({
            "source": int(u),
            "target": int(v),
            "weight": int(d['weight'])
        })

    # User data: which node each user is currently attached to
    users_data = []
    for usr in users:
        users_data.append({
            "id": usr.user_id,
            "node": int(usr.current_node),
            "traffic_type": usr.traffic_type
        })

    topology = {
        "num_nodes": len(G.nodes()),
        "nodes": nodes_data,
        "edges": edges_data,
        "upfs": [int(u) for u in upfs],
        "users": users_data
    }

    with open(filename, 'w') as f:
        json.dump(topology, f, indent=2)

    print(f"  [✓] Topology exported → {filename}")
    return filename

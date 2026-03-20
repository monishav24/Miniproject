import networkx as nx
import random

def create_network(n=30, m=2):
    """
    Creates a Barabási–Albert graph to represent the 5G core network topology.
    """
    G = nx.barabasi_albert_graph(n, m)
    for u, v in G.edges():
        # Representing base delay or distance between nodes
        G[u][v]['weight'] = random.randint(1, 10)
    
    # Add random positions for each node for NetAnim visualization
    for i in G.nodes():
        G.nodes[i]['pos'] = (random.uniform(0, 100), random.uniform(0, 100))
        
    return G

"""
mobility_model.py
Simulates user mobility using a random walk model across the network graph.
"""
import random


def random_walk(users, G):
    """
    Each user has a 60% chance of moving to a random neighbor node
    at each time step, simulating realistic mobility patterns.
    """
    for user in users:
        neighbors = list(G.neighbors(user.current_node))
        if neighbors and random.random() < 0.6:
            user.current_node = random.choice(neighbors)

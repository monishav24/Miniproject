import random

def random_walk(users, G):
    """
    Simulates user mobility using a random walk model.
    """
    for user in users:
        neighbors = list(G.neighbors(user.current_node))
        if neighbors and random.random() < 0.6:  # 60% chance to move to a neighbor
            user.current_node = random.choice(neighbors)

import random

class User:
    def __init__(self, user_id, start_node):
        self.user_id = user_id
        self.current_node = start_node
        self.traffic_type = random.choice(['eMBB', 'URLLC', 'mMTC'])
        
        # Define SLA required latency based on traffic type
        if self.traffic_type == 'URLLC':
            self.req_latency = 10
        elif self.traffic_type == 'eMBB':
            self.req_latency = 40
        else:
            self.req_latency = 100

def generate_users(G, num_users=100):
    users = []
    nodes = list(G.nodes())
    for i in range(num_users):
        users.append(User(i, random.choice(nodes)))
    return users

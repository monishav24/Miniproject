import matplotlib.pyplot as plt
from cost_function import calculate_cost

def plot_metrics(metrics_dict, filename):
    time_steps = len(next(iter(metrics_dict.values()))['latency'])
    x = range(time_steps)
    
    plt.figure(figsize=(14, 10))
    
    # Latency Plot
    plt.subplot(2, 2, 1)
    for algo, data in metrics_dict.items():
        plt.plot(x, data['latency'], label=algo)
    plt.title('Average Latency over Time')
    plt.xlabel('Time Step')
    plt.ylabel('Latency (ms)')
    plt.legend()
    
    # Energy Plot
    plt.subplot(2, 2, 2)
    for algo, data in metrics_dict.items():
        plt.plot(x, data['energy'], label=algo)
    plt.title('Energy Consumption over Time')
    plt.xlabel('Time Step')
    plt.ylabel('Energy (Units)')
    plt.legend()
    
    # SLA Violations Plot
    plt.subplot(2, 2, 3)
    for algo, data in metrics_dict.items():
        plt.plot(x, data['sla'], label=algo)
    plt.title('SLA Violations over Time')
    plt.xlabel('Time Step')
    plt.ylabel('Violations')
    plt.legend()
    
    # Cost Plot
    plt.subplot(2, 2, 4)
    for algo, data in metrics_dict.items():
        costs = [calculate_cost(l, e, s) for l, e, s in zip(data['latency'], data['energy'], data['sla'])]
        plt.plot(x, costs, label=algo)
    plt.title('Total Operational Cost over Time')
    plt.xlabel('Time Step')
    plt.ylabel('Cost')
    plt.legend()
    
    plt.tight_layout()
    plt.savefig(filename)
    plt.close()

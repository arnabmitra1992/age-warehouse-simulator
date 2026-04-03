import networkx as nx
import matplotlib.pyplot as plt
import numpy as np

class AGV:
    def __init__(self, agv_id, speed, capacity):
        self.agv_id = agv_id
        self.speed = speed
        self.capacity = capacity
        self.current_location = None
        self.destination = None
        self.cargo = 0

    def move_to(self, destination):
        self.current_location = destination
        print(f"AGV {self.agv_id} moving to {destination}.")

class Warehouse:
    def __init__(self):
        self.graph = nx.Graph()
        self.ags = []

    def add_nodes(self, nodes):
        self.graph.add_nodes_from(nodes)

    def add_edges(self, edges):
        self.graph.add_edges_from(edges)

    def display_layout(self):
        pos = nx.spring_layout(self.graph)
        nx.draw(self.graph, pos, with_labels=True)
        plt.show()

    def add_agv(self, agv):
        self.ags.append(agv)

    def simulate(self):
        for agv in self.ags:
            agv.move_to(np.random.choice(self.graph.nodes))

# Example use of the simulator
if __name__ == '__main__':
    warehouse = Warehouse()
    warehouse.add_nodes(['Node1', 'Node2', 'Node3', 'Node4'])
    warehouse.add_edges([('Node1', 'Node2'), ('Node2', 'Node3'), ('Node3', 'Node4')])
    warehouse.display_layout()
    agv1 = AGV(agv_id=1, speed=5, capacity=10)
    warehouse.add_agv(agv1)
    warehouse.simulate()
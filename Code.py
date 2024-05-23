import pandas as pd
import networkx as nx
import time
import csv
from datetime import datetime, timedelta
# import matplotlib.pyplot as plt

"""
To debug the code and see what is happening, several commenetd print statements are provided, which can be uncommented to see how the algorithm is being executed.
"""

# Function to load data
def load_data():
    passengers = pd.read_csv('passengers.csv')
    flights = pd.read_csv('flights.csv')
    canceled_flights = pd.read_csv('canceled.csv')
    return passengers, flights, canceled_flights

# Function to check if a connection is valid
def is_valid_connection(arr_time1, dep_time2):
    # Minimum layover time (e.g., 30 minutes)
    min_layover = timedelta(minutes=30)
    # Check if the layover is valid
    return (dep_time2 - arr_time1) >= min_layover

# Function to find reallocation path using BFS
def find_reallocation_path(passenger, G, flights_df, canceled_flights, max_flights=3):
    start_airport = flights_df[flights_df['FID'] == passenger['FID']]['DEP'].values[0]
    end_airport = flights_df[flights_df['FID'] == passenger['FID']]['ARR'].values[0]

    # print("Start airport:", start_airport)
    # print("End airport:", end_airport)

    # Check if start and end airports exist in the graph
    if start_airport not in G.nodes or end_airport not in G.nodes:
        print("Start or end airport not in graph.")
        return []
    
    original_dep_time = flights_df[flights_df['FID'] == passenger['FID']]['DEP_TIME'].values[0]
    original_arr_time = flights_df[flights_df['FID'] == passenger['FID']]['ARR_TIME'].values[0]

    # Convert epoch times to datetime
    original_dep_time = datetime.fromtimestamp(original_dep_time)
    original_arr_time = datetime.fromtimestamp(original_arr_time)

    # BFS initialization
    queue = [(start_airport, [], original_dep_time)]
    visited = set()

    while queue:
        current_airport, path, current_time = queue.pop(0)
        
        # print("Start airport:", start_airport)
        # print("End airport:", end_airport)
        # print("Current airport:", current_airport)
        # print("Current path:", path)
        # print("Current time:", current_time)
        
        if current_airport == end_airport and len(path) <= max_flights:
        # Decrement capacity to simulate seat allocation
            for flight_id in path:
                for neighbor in G.successors(current_airport):
                    # print("Neighbor of", current_airport, ":", neighbor)
                    if G[current_airport][neighbor]['FID'] == flight_id:
                        G[current_airport][neighbor]['CAPACITY'] -= 1
            return path


        if path and len(path) < max_flights:
            for neighbor in G.successors(current_airport):
                flight_data = G[current_airport][neighbor]
                # print("Flight data:", flight_data)
                flight_id = flight_data['FID']
                dep_time = datetime.fromtimestamp(flight_data['DEP_TIME'])
                arr_time = datetime.fromtimestamp(flight_data['ARR_TIME'])
                capacity = flight_data['CAPACITY']

                if (flight_id not in path and 
                    is_valid_connection(current_time, dep_time) and 
                    flight_id not in visited):

                    queue.append((neighbor, path + [flight_id], arr_time))
                    visited.add(flight_id)
                
    return []

# Main function
def main():
    start_time = time.time()

    # Load data
    passengers, flights, canceled_flights = load_data()

    # Identify affected passengers
    affected_passengers = passengers[passengers['FID'].isin(canceled_flights['Canceled'])]

    # Create graph from flights
    G = nx.DiGraph()

    # 'flights' is the DataFrame containing flight data
    for _, row in flights.iterrows():
        # Add nodes for departure and arrival airports
        G.add_node(row['DEP'])
        G.add_node(row['ARR'])
    
        # Add directed edge from departure to arrival
        G.add_edge(
            row['DEP'],  # Source node (departure airport)
            row['ARR'],  # Target node (arrival airport)
            FID=row['FID'],  # Flight ID
            DEP=row['DEP'],  # Departure airport
            ARR=row['ARR'],  # Arrival airport
            DEP_TIME=row['DEP_TIME'],  # Departure time
            ARR_TIME=row['ARR_TIME'],  # Arrival time
            CAPACITY=row['CAPACITY']  # Flight capacity
        )
 
   # for _, flight in flights.iterrows():
    #    dep = flight['DEP']
    #    arr = flight['ARR']
    #    capacity = flight['CAPACITY']
    #    print(f"Flight from {dep} to {arr} has capacity: {capacity}")
    
    reallocations = []
    original_arrival_times = {}
    new_arrival_times = {}

    for _, passenger in affected_passengers.iterrows():
        # print("Finding reallocation path for passenger:", passenger['PID'])
        path = find_reallocation_path(passenger, G, flights, canceled_flights, max_flights=3)
        reallocations.append((passenger['PID'], path))

        # Store original and new arrival times for calculating the average absolute difference
        if path:
            original_arrival_time = flights[flights['FID'] == passenger['FID']]['ARR_TIME'].values[0]
            new_arrival_time = flights[flights['FID'] == path[-1]]['ARR_TIME'].values[0]
            original_arrival_times[passenger['PID']] = original_arrival_time
            new_arrival_times[passenger['PID']] = new_arrival_time

    # Calculate metrics
    num_affected = len(affected_passengers)
    num_reallocated = sum(1 for _, path in reallocations if path)
    avg_layovers = sum(len(path) - 1 for _, path in reallocations if path) / num_reallocated if num_reallocated > 0 else 0

    # Calculate average absolute difference in arrival time
    total_difference = sum(abs(new_arrival_times[pid] - original_arrival_times[pid]) for pid in new_arrival_times)
    avg_arrival_diff = total_difference / num_reallocated if num_reallocated > 0 else 0

    end_time = time.time()
    exec_time = (end_time - start_time) * 1000  # Convert to milliseconds

    stats = {
        "Affected": num_affected,
        "Reallocated": num_reallocated,
        "AvgLay": avg_layovers,
        "TimeDiff": avg_arrival_diff,
        "SolTime": exec_time
    }

    # Write stats.csv
    with open('stats.csv', 'w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(["Affected", "Reallocated", "AvgLay", "TimeDiff", "SolTime"])
        writer.writerow([stats["Affected"], stats["Reallocated"], stats["AvgLay"], stats["TimeDiff"], stats["SolTime"]])

    # Write allot.csv
    with open('allot.csv', 'w', newline='') as file:
        writer = csv.writer(file)
        for passenger_id, path in reallocations:
            writer.writerow([passenger_id, len(path)] + path)

    # Optional visualization
    # pos = nx.spring_layout(G)
    # nx.draw(G, pos, with_labels=True, node_size=500, node_color="skyblue", font_size=10, font_weight="bold")
    # plt.show()


if __name__ == "__main__":
    main()
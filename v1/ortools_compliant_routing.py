import pandas as pd
import numpy as np
import math
from ortools.constraint_solver import routing_enums_pb2
from ortools.constraint_solver import pywrapcp

print("1. Loading Data...")
# We use the Phase A plan because it already mapped Customers to Farms
df = pd.read_excel('Phase_A_Fulfillment_Plan.xlsx')

# --- STRICT DATASET COMPLIANCE ---
FUEL_PRICE = 2.05
VEHICLES = [
    {'name': 'REEFER_TRK', 'cap': 400, 'cold': 1, 'fixed': 450, 'fuel_km': 0.38, 'maint_km': 0.36},
    {'name': 'REEFER_TRK', 'cap': 400, 'cold': 1, 'fixed': 450, 'fuel_km': 0.38, 'maint_km': 0.36},
    {'name': 'LORRY_AMB',  'cap': 500, 'cold': 0, 'fixed': 280, 'fuel_km': 0.32, 'maint_km': 0.30},
    {'name': 'LORRY_AMB',  'cap': 500, 'cold': 0, 'fixed': 280, 'fuel_km': 0.32, 'maint_km': 0.30},
    {'name': 'VAN_AMB',    'cap': 120, 'cold': 0, 'fixed': 120, 'fuel_km': 0.12, 'maint_km': 0.22},
    {'name': 'VAN_AMB',    'cap': 120, 'cold': 0, 'fixed': 120, 'fuel_km': 0.12, 'maint_km': 0.22},
] # Giving the algorithm a small mixed fleet to choose from

def get_distance(lat1, lon1, lat2, lon2):
    R = 6371.0
    lat1, lon1, lat2, lon2 = map(np.radians, [lat1, lon1, lat2, lon2])
    a = np.sin((lat2 - lat1)/2)**2 + np.cos(lat1) * np.cos(lat2) * np.sin((lon2 - lon1)/2)**2
    c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1-a))
    return (R * c) * 1.3  # Official 1.3 circuity multiplier

# We will route the busiest farm to demonstrate
target_farm = df['farm_id'].value_counts().idxmax()
df_farm = df[df['farm_id'] == target_farm].copy()

# Group orders by customer
customer_group = df_farm.groupby(['customer_id', 'cust_lat', 'cust_lon']).agg({
    'weekly_demand_mean_boxes': 'sum',
    'strict_cold_chain': 'max' # If ANY item needs cold, the whole drop needs cold
}).reset_index()

farm_lat = df_farm['farm_lat'].iloc[0]
farm_lon = df_farm['farm_lon'].iloc[0]

locations = [(farm_lat, farm_lon)] + list(zip(customer_group['cust_lat'], customer_group['cust_lon']))
demands = [0] + customer_group['weekly_demand_mean_boxes'].astype(int).tolist()
cold_reqs = [0] + customer_group['strict_cold_chain'].astype(int).tolist()
customer_ids = ["FARM"] + customer_group['customer_id'].tolist()

print(f"2. Building Distance Matrix for {target_farm} ({len(customer_ids)-1} Customers)...")
distance_matrix = []
for i in range(len(locations)):
    row = []
    for j in range(len(locations)):
        row.append(int(get_distance(locations[i][0], locations[i][1], locations[j][0], locations[j][1])))
    distance_matrix.append(row)

# Set up OR-Tools Data
data = {
    'distance_matrix': distance_matrix,
    'demands': demands,
    'vehicle_capacities': [v['cap'] for v in VEHICLES],
    'num_vehicles': len(VEHICLES),
    'depot': 0
}

# --- INITIALIZE OR-TOOLS ---
manager = pywrapcp.RoutingIndexManager(len(data['distance_matrix']), data['num_vehicles'], data['depot'])
routing = pywrapcp.RoutingModel(manager)

# 1. Distance & Cost Callback
# Instead of just distance, we calculate the EXACT RM COST for the specific vehicle
def cost_callback(from_index, to_index, vehicle_id):
    from_node = manager.IndexToNode(from_index)
    to_node = manager.IndexToNode(to_index)
    dist_km = data['distance_matrix'][from_node][to_node]
    
    v = VEHICLES[vehicle_id]
    # Cost = (Fuel * Price) + Maintenance (Fixed cost is added later if truck is used)
    variable_cost_rm = (dist_km * v['fuel_km'] * FUEL_PRICE) + (dist_km * v['maint_km'])
    
    # --- COLD CHAIN ENFORCEMENT ---
    # If the destination needs cold, and this truck is NOT cold, make the cost infinite (illegal)
    if to_node != 0 and cold_reqs[to_node] == 1 and v['cold'] == 0:
        return 999999 
        
    return int(variable_cost_rm * 100) # OR-Tools needs integers

# Register a separate cost callback for EVERY vehicle in the fleet
for vehicle_id in range(data['num_vehicles']):
    cost_cb_index = routing.RegisterTransitCallback(lambda from_idx, to_idx, vid=vehicle_id: cost_callback(from_idx, to_idx, vid))
    routing.SetArcCostEvaluatorOfVehicle(cost_cb_index, vehicle_id)
    # Add Fixed Cost if the vehicle leaves the depot
    routing.SetFixedCostOfVehicle(int(VEHICLES[vehicle_id]['fixed'] * 100), vehicle_id)

# 2. Capacity Constraint
def demand_callback(from_index):
    from_node = manager.IndexToNode(from_index)
    return data['demands'][from_node]

demand_callback_index = routing.RegisterUnaryTransitCallback(demand_callback)
routing.AddDimensionWithVehicleCapacity(
    demand_callback_index,
    0, data['vehicle_capacities'], True, 'Capacity')

# --- SOLVE ---
print("3. Solving for the Absolute Lowest RM Cost Route...")
search_parameters = pywrapcp.DefaultRoutingSearchParameters()
search_parameters.first_solution_strategy = routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
search_parameters.time_limit.seconds = 10 # Let it think for 10 seconds

solution = routing.SolveWithParameters(search_parameters)

# --- OUTPUT ---
if solution:
    print(f"\nOPTIMAL ROUTE FOUND FOR {target_farm}\n" + "="*50)
    total_cost_rm = 0
    
    for vehicle_id in range(data['num_vehicles']):
        index = routing.Start(vehicle_id)
        
        # If the truck doesn't leave the farm, skip it
        if routing.IsEnd(solution.Value(routing.NextVar(index))):
            continue
            
        v = VEHICLES[vehicle_id]
        plan_output = f"[{v['name']}] (Cap: {v['cap']} | Cold: {v['cold']})\n   Path: "
        
        route_dist = 0
        route_load = 0
        
        while not routing.IsEnd(index):
            node_index = manager.IndexToNode(index)
            route_load += data['demands'][node_index]
            plan_output += f"{customer_ids[node_index]} -> "
            previous_index = index
            index = solution.Value(routing.NextVar(index))
            route_dist += data['distance_matrix'][manager.IndexToNode(previous_index)][manager.IndexToNode(index)]
            
        plan_output += "FARM"
        
        # Calculate exact cost for this specific truck
        truck_cost = v['fixed'] + (route_dist * v['fuel_km'] * FUEL_PRICE) + (route_dist * v['maint_km'])
        total_cost_rm += truck_cost
        
        print(plan_output)
        print(f"   Load: {route_load} / {v['cap']} boxes")
        print(f"   Distance: {route_dist} km | Cost: RM {truck_cost:.2f}\n" + "-"*50)
        
    print(f"TOTAL OPTIMIZED COST: RM {total_cost_rm:.2f}")
    print("="*50)
else:
    print('No solution found! You might need to add more vehicles to the fleet array.')
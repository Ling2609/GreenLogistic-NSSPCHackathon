import pandas as pd
import math

FILE_NAME = 'Dataset_Preliminary_Presentation_v10 (1).xlsx'

print("========================================")
print(" STEP 4: PHASE B (ROUTING & COSTS)")
print("========================================")

# ---------------------------------------------------------
# 1. LOAD DYNAMIC DATA
# ---------------------------------------------------------
print("1. Loading dynamic vehicle and scenario data from Excel...")
df_vehicles = pd.read_excel(FILE_NAME, sheet_name='Vehicles')
df_scenarios = pd.read_excel(FILE_NAME, sheet_name='Scenarios')

# We use the perfect allocation list we just built in Step 3!
df_plan = pd.read_excel("Step3_Final_Fulfillment_Plan.xlsx")

# ---------------------------------------------------------
# 2. CONVERT TABLES TO DICTIONARIES FOR THE ALGORITHM
# ---------------------------------------------------------
# This takes the Vehicles Excel sheet and turns it into a lookup dictionary automatically!
# e.g. vehicles_dict['REEFER_TRK']['capacity_boxes']
vehicles_dict = df_vehicles.set_index('vehicle_type_id').to_dict('index')

# The README states fuel is 2.05 RM. We set it as a variable so it's easy to change.
FUEL_PRICE_RM = 2.05

# For this baseline, we will look at Scenario S0 (Normal Week)
s0_data = df_scenarios[df_scenarios['scenario_id'] == 'S0'].iloc[0]
travel_time_multiplier = s0_data['travel_time_multiplier']

# ---------------------------------------------------------
# 3. ROUTING & PACKING ENGINE
# ---------------------------------------------------------
print("2. Grouping orders into truck routes...")

route_records = []

# Group all allocated boxes by Farm and Customer 
for (farm, customer), group in df_plan.groupby(['farm_id', 'customer_id']):
    
    # Get route details (they are the same for the whole group)
    distance_km = group['distance_km'].iloc[0] # Using raw distance
    road_distance_km = distance_km * 1.3 # 1.3 Circuity factor
    max_lead_time = group['max_lead_time_h'].iloc[0]
    
    # Separate cold boxes from ambient boxes
    cold_boxes = group[group['strict_cold_chain'] == 1]['allocated_boxes'].sum()
    ambient_boxes = group[group['strict_cold_chain'] == 0]['allocated_boxes'].sum()
    
    trucks_used = []
    
    # --- PACKING LOGIC ---
    # 1. Handle Cold Boxes
    if cold_boxes > 0:
        reefer = vehicles_dict['REEFER_TRK']
        num_reefers = math.ceil(cold_boxes / reefer['capacity_boxes'])
        trucks_used.extend(['REEFER_TRK'] * num_reefers)
        
        # Optimize: Stuff leftover ambient boxes into the empty space of the Reefer!
        spare_capacity = (num_reefers * reefer['capacity_boxes']) - cold_boxes
        overflow = min(spare_capacity, ambient_boxes)
        ambient_boxes -= overflow

    # 2. Handle Remaining Ambient Boxes
    while ambient_boxes > 0:
        lorry = vehicles_dict['LORRY_AMB']
        van = vehicles_dict['VAN_AMB']
        
        # If we have a lot, use a Lorry
        if ambient_boxes > van['capacity_boxes']:
            trucks_used.append('LORRY_AMB')
            ambient_boxes -= lorry['capacity_boxes']
        # If it's a small amount, use a Van
        else:
            trucks_used.append('VAN_AMB')
            ambient_boxes -= van['capacity_boxes']
            
    # --- CALCULATE COSTS FOR THE ASSIGNED TRUCKS ---
    for truck_id in trucks_used:
        v = vehicles_dict[truck_id]
        
        travel_time_h = (road_distance_km / v['avg_speed_kmph']) * travel_time_multiplier
        fuel_liters = road_distance_km * v['fuel_l_per_km']
        fuel_cost = fuel_liters * FUEL_PRICE_RM
        maint_cost = road_distance_km * v['maintenance_rm_per_km']
        
        total_trip_cost = v['fixed_cost_per_trip_rm'] + fuel_cost + maint_cost
        
        # Check if it arrived before the customer's deadline
        on_time = 1 if travel_time_h <= max_lead_time else 0
        
        route_records.append({
            'farm_id': farm,
            'customer_id': customer,
            'vehicle_type': truck_id,
            'road_distance_km': round(road_distance_km, 2),
            'travel_time_h': round(travel_time_h, 2),
            'on_time': on_time,
            'total_cost_rm': round(total_trip_cost, 2)
        })

df_routes = pd.DataFrame(route_records)

# ---------------------------------------------------------
# 4. PRINT SUMMARY KPIs
# ---------------------------------------------------------
print("\n--- PHASE B: BASELINE (S0) SUMMARY ---")
print(f"Total Unique Delivery Routes: {len(df_routes)}")
print(f"Total Vehicles Dispatched: {len(df_routes)}")
print(f"Fleet Breakdown:\n{df_routes['vehicle_type'].value_counts().to_string()}")
print(f"On-Time Delivery Rate: {(df_routes['on_time'].sum() / len(df_routes)) * 100:.1f}%")
print(f"\nTOTAL SYSTEM COST: RM {df_routes['total_cost_rm'].sum():,.2f}")
print("========================================\n")

df_routes.to_excel("Step4_Baseline_Routes.xlsx", index=False)
print("Saved route details to 'Step4_Baseline_Routes.xlsx'")
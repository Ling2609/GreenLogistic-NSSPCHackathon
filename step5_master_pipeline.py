import pandas as pd
import numpy as np
import math

FILE_NAME = 'Dataset_Preliminary_Presentation_v10 (1).xlsx'

print("========================================")
print(" STEP 5: THE MASTER SCENARIO PIPELINE")
print("========================================")

# ---------------------------------------------------------
# 1. LOAD ALL DYNAMIC DATA FROM EXCEL
# ---------------------------------------------------------
print("1. Loading dynamic data...")
df_farms         = pd.read_excel(FILE_NAME, sheet_name='Farms')
df_products      = pd.read_excel(FILE_NAME, sheet_name='Products')
df_farm_products = pd.read_excel(FILE_NAME, sheet_name='Farm_Products')
df_demand        = pd.read_excel(FILE_NAME, sheet_name='Demand')
df_customers     = pd.read_excel(FILE_NAME, sheet_name='Customers')
df_vehicles      = pd.read_excel(FILE_NAME, sheet_name='Vehicles')
df_scenarios     = pd.read_excel(FILE_NAME, sheet_name='Scenarios')
df_yields        = pd.read_excel(FILE_NAME, sheet_name='Scenario_Yield')

def clean_ids(df, id_columns):
    for col in id_columns:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip().str.upper()
    return df

df_farms         = clean_ids(df_farms, ['farm_id', 'location_id'])
df_products      = clean_ids(df_products, ['sku_id'])
df_farm_products = clean_ids(df_farm_products, ['farm_id', 'sku_id'])
df_demand        = clean_ids(df_demand, ['customer_id', 'sku_id'])
df_customers     = clean_ids(df_customers, ['customer_id'])

# Setup Master Menus
df_supply = pd.merge(df_farm_products, df_farms, on='farm_id', how='left')
df_supply = pd.merge(df_supply, df_products, on='sku_id', how='left')
df_supply.rename(columns={'lat': 'farm_lat', 'lon': 'farm_lon'}, inplace=True)

df_demand_menu = pd.merge(df_demand, df_customers, on='customer_id', how='left')
df_demand_menu.rename(columns={'lat': 'cust_lat', 'lon': 'cust_lon'}, inplace=True)

def get_distance(lat1, lon1, lat2, lon2):
    R = 6371.0 
    lat1, lon1, lat2, lon2 = map(np.radians, [lat1, lon1, lat2, lon2])
    a = np.sin((lat2 - lat1)/2)**2 + np.cos(lat1) * np.cos(lat2) * np.sin((lon2 - lon1)/2)**2
    c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1-a))
    return (R * c) * 1.3

df_matches_base = pd.merge(df_demand_menu, df_supply, on='sku_id', how='inner')
df_matches_base['distance_km'] = get_distance(
    df_matches_base['farm_lat'], df_matches_base['farm_lon'], 
    df_matches_base['cust_lat'], df_matches_base['cust_lon']
)
df_matches_base['strict_cold_chain'] = df_matches_base[['cold_storage_requested', 'cold_required']].max(axis=1)
df_matches_base = df_matches_base.sort_values(by=['customer_id', 'sku_id', 'distance_km'])

vehicles_dict = df_vehicles.set_index('vehicle_type_id').to_dict('index')
FUEL_PRICE_RM = 2.05

summary_kpis = []
# This dictionary will store our Side-by-Side Wide Table format!
master_routes_dict = {}

# ---------------------------------------------------------
# 2. RUN THE PIPELINE FOR EACH SCENARIO
# ---------------------------------------------------------
print("\n2. Executing Scenarios...")

for _, scenario in df_scenarios.iterrows():
    s_id = scenario['scenario_id']
    print(f"   -> Running {s_id}: {scenario['scenario_name']}")
    
    d_mult = scenario['demand_multiplier']
    t_mult = scenario['travel_time_multiplier']
    
    # --- PHASE A: ALLOCATION ---
    df_matches = df_matches_base.copy()
    
    customer_demand = df_matches.groupby(['customer_id', 'sku_id'])['weekly_demand_mean_boxes'].max() * d_mult
    customer_demand = customer_demand.to_dict()
    
    farm_inventory = {}
    for (farm, sku, loc), group in df_matches.groupby(['farm_id', 'sku_id', 'location_id']):
        cap = group['daily_capacity_boxes'].max()
        y_mult = df_yields[(df_yields['scenario_id'] == s_id) & (df_yields['location_id'] == loc)]['yield_multiplier'].max()
        if pd.isna(y_mult): y_mult = 1.0
            
        farm_inventory[(farm, sku)] = cap * y_mult

    final_allocations = []
    for index, row in df_matches.iterrows():
        cust, sku, farm = row['customer_id'], row['sku_id'], row['farm_id']
        needed = customer_demand.get((cust, sku), 0)
        avail = farm_inventory.get((farm, sku), 0)
        
        if needed <= 0 or avail <= 0: continue
            
        move = min(needed, avail)
        customer_demand[(cust, sku)] -= move
        farm_inventory[(farm, sku)] -= move
        
        record = row.copy()
        record['allocated_boxes'] = move
        final_allocations.append(record)

    df_plan = pd.DataFrame(final_allocations)
    
    # --- PHASE B: ROUTING & COSTS ---
    total_scenario_trucks = 0
    total_scenario_cost = 0
    total_scenario_ontime = 0
    total_dispatched = 0
    
    for (farm, customer), group in df_plan.groupby(['farm_id', 'customer_id']):
        dist = group['distance_km'].max()
        max_lead = group['max_lead_time_h'].max()
        
        cold_boxes = group[group['strict_cold_chain'] == 1]['allocated_boxes'].sum()
        ambient_boxes = group[group['strict_cold_chain'] == 0]['allocated_boxes'].sum()
        total_dispatched += cold_boxes + ambient_boxes
        
        trucks = []
        if cold_boxes > 0:
            reefer = vehicles_dict['REEFER_TRK']
            num_reefers = math.ceil(cold_boxes / reefer['capacity_boxes'])
            trucks.extend(['REEFER_TRK'] * num_reefers)
            spare = (num_reefers * reefer['capacity_boxes']) - cold_boxes
            overflow = min(spare, ambient_boxes)
            ambient_boxes -= overflow

        while ambient_boxes > 0:
            if ambient_boxes > vehicles_dict['VAN_AMB']['capacity_boxes']:
                trucks.append('LORRY_AMB')
                ambient_boxes -= vehicles_dict['LORRY_AMB']['capacity_boxes']
            else:
                trucks.append('VAN_AMB')
                ambient_boxes -= vehicles_dict['VAN_AMB']['capacity_boxes']
                
        # Calculate specific costs for this route grouping
        total_route_cost = 0
        max_time = 0
        for t in trucks:
            v = vehicles_dict[t]
            time_h = (dist / v['avg_speed_kmph']) * t_mult
            if time_h > max_time: max_time = time_h
            total_route_cost += v['fixed_cost_per_trip_rm'] + (dist * v['fuel_l_per_km'] * FUEL_PRICE_RM) + (dist * v['maintenance_rm_per_km'])
            
        on_time = 1 if max_time <= max_lead else 0
        
        total_scenario_trucks += len(trucks)
        total_scenario_cost += total_route_cost
        total_scenario_ontime += on_time * len(trucks)

        # ---------------------------------------------------------
        # THE "WIDE-FORMAT" BUILDER (Exactly what you asked for!)
        # ---------------------------------------------------------
        # Group trucks like "1x REEFER_TRK + 2x VAN_AMB"
        from collections import Counter
        truck_counts = Counter(trucks)
        truck_str = " + ".join([f"{v}x {k}" for k, v in truck_counts.items()])
        
        key = (farm, customer)
        if key not in master_routes_dict:
            master_routes_dict[key] = {
                'Farm': farm,
                'Customer': customer,
                'Trucks': truck_str,
                'Time_H': round(max_time, 2),
                'On_Time': on_time
            }
            
        # Dynamically append Dist and Cost for whatever Scenario we are in!
        master_routes_dict[key][f'Dist_{s_id}'] = round(dist, 2)
        master_routes_dict[key][f'Cost_{s_id}'] = round(total_route_cost, 2)
        
        # If it's the normal baseline (S0), lock in those truck requirements
        if s_id == 'S0':
            master_routes_dict[key]['Trucks'] = truck_str
            master_routes_dict[key]['Time_H'] = round(max_time, 2)
            master_routes_dict[key]['On_Time'] = on_time

    # Calculate overall Dashboard summary
    on_time_pct = (total_scenario_ontime / total_scenario_trucks) * 100 if total_scenario_trucks > 0 else 0
    summary_kpis.append({
        'Scenario': s_id,
        'Name': scenario['scenario_name'],
        'Total Trucks': total_scenario_trucks,
        'Total Cost (RM)': round(total_scenario_cost, 2),
        'On-Time %': round(on_time_pct, 1),
        'Boxes Moved': round(total_dispatched, 0)
    })

# ---------------------------------------------------------
# 3. EXPORT FINAL REPORT 
# ---------------------------------------------------------
df_summary = pd.DataFrame(summary_kpis)
df_summary.set_index('Scenario', inplace=True)
df_pivot = df_summary.T 

# Convert our Wide Dictionary into the final DataFrame!
df_wide_routes = pd.DataFrame(list(master_routes_dict.values()))
# If a route wasn't used in a disaster scenario, put 0 instead of leaving it blank
df_wide_routes.fillna(0, inplace=True) 

# Sort it alphabetically by Farm and Customer so it is easy to read
df_wide_routes.sort_values(by=['Farm', 'Customer'], inplace=True)

print("\n========================================")
print("    FINAL SIDE-BY-SIDE DASHBOARD")
print("========================================")
print(df_pivot.to_string())
print("========================================")

with pd.ExcelWriter("Step5_Master_Scenario_Results.xlsx") as writer:
    df_pivot.to_excel(writer, sheet_name='Comparison_Dashboard')
    df_wide_routes.to_excel(writer, sheet_name='Wide_Route_Comparison', index=False)

print("\nSuccess! Pipeline finished and exported to 'Step5_Master_Scenario_Results.xlsx'")
import pandas as pd
import numpy as np
import math
import random
from collections import Counter
import os

# ============================================================
# STEP 6: PROPOSAL B (REGIONAL "MILK RUN" CONSOLIDATION)
#
# Features:
#   1. True AI "Nearest Neighbor" TSP Routing Algorithm
#   2. Groups by Farm + Region + Cold Chain Rules
#   3. Strict adherence to dataset constraints (0.8 Yield Shock)
#   4. Side-by-Side Pastel KPI Dashboard
#   5. Data Dictionary Included
# ============================================================

# Auto-locate the dataset in the same folder as this script
script_dir = os.path.dirname(os.path.abspath(__file__))
FILE_NAME = os.path.join(script_dir, 'Dataset_Preliminary_Presentation_v10 (1).xlsx')

FUEL_PRICE_RM = 2.05   
YIELD_SHOCK   = 0.8    

print("========================================")
print(" STEP 6: PROPOSAL B (TRUE AI CONSOLIDATION)")
print("========================================")

# ---------------------------------------------------------
# 1. LOAD & CLEAN DATA
# ---------------------------------------------------------
print("\n1. Loading and cleaning dataset...")
df_farms         = pd.read_excel(FILE_NAME, sheet_name='Farms')
df_products      = pd.read_excel(FILE_NAME, sheet_name='Products')
df_farm_products = pd.read_excel(FILE_NAME, sheet_name='Farm_Products')
df_demand        = pd.read_excel(FILE_NAME, sheet_name='Demand')
df_customers     = pd.read_excel(FILE_NAME, sheet_name='Customers')
df_vehicles      = pd.read_excel(FILE_NAME, sheet_name='Vehicles')

def clean_ids(df, cols):
    for c in cols:
        if c in df.columns:
            df[c] = df[c].astype(str).str.strip().str.upper()
    return df

df_farms         = clean_ids(df_farms,         ['farm_id', 'location_id'])
df_products      = clean_ids(df_products,       ['sku_id'])
df_farm_products = clean_ids(df_farm_products,  ['farm_id', 'sku_id'])
df_demand        = clean_ids(df_demand,         ['customer_id', 'sku_id'])
df_customers     = clean_ids(df_customers,      ['customer_id'])

# Safely determine the region column for grouping
region_col = 'state' if 'state' in df_customers.columns else 'city' if 'city' in df_customers.columns else 'customer_id'

df_supply = pd.merge(df_farm_products, df_farms, on='farm_id', how='left')
df_supply = pd.merge(df_supply, df_products, on='sku_id', how='left')
df_supply.rename(columns={'lat': 'farm_lat', 'lon': 'farm_lon'}, inplace=True)

df_demand_menu = pd.merge(df_demand, df_customers, on='customer_id', how='left')
df_demand_menu.rename(columns={'lat': 'cust_lat', 'lon': 'cust_lon'}, inplace=True)

vehicles_dict = df_vehicles.set_index('vehicle_type_id').to_dict('index')

# ---------------------------------------------------------
# 2. MATCHING & DISTANCE MATH
# ---------------------------------------------------------
def haversine_road(lat1, lon1, lat2, lon2):
    R = 6371.0
    lat1, lon1, lat2, lon2 = map(np.radians, [lat1, lon1, lat2, lon2])
    a = np.sin((lat2-lat1)/2)**2 + np.cos(lat1)*np.cos(lat2)*np.sin((lon2-lon1)/2)**2
    return R * 2 * np.arctan2(np.sqrt(a), np.sqrt(1-a)) * 1.3

df_all_matches = pd.merge(df_demand_menu, df_supply, on='sku_id', how='inner')
df_all_matches['distance_km'] = haversine_road(
    df_all_matches['farm_lat'], df_all_matches['farm_lon'],
    df_all_matches['cust_lat'], df_all_matches['cust_lon']
)
df_all_matches['strict_cold_chain'] = df_all_matches[['cold_storage_requested', 'cold_required']].max(axis=1)
df_all_matches = df_all_matches.sort_values(['customer_id', 'sku_id', 'distance_km']).reset_index(drop=True)

# ---------------------------------------------------------
# 3. THE TRUE AI: NEAREST NEIGHBOR ROUTING ALGORITHM
# ---------------------------------------------------------
def calculate_tsp_route(farm_lat, farm_lon, group_df):
    unique_custs = group_df[['customer_id', 'cust_lat', 'cust_lon']].drop_duplicates().to_dict('records')
    curr_lat, curr_lon = farm_lat, farm_lon
    total_route_distance = 0.0
    
    unvisited = list(unique_custs)
    
    while unvisited:
        best_dist = float('inf')
        best_idx = 0
        for i, c in enumerate(unvisited):
            d = haversine_road(curr_lat, curr_lon, c['cust_lat'], c['cust_lon'])
            if d < best_dist:
                best_dist = d
                best_idx = i
        
        next_stop = unvisited.pop(best_idx)
        total_route_distance += best_dist
        curr_lat, curr_lon = next_stop['cust_lat'], next_stop['cust_lon']
        
    return total_route_distance

# ---------------------------------------------------------
# 4. SCENARIOS & MAIN LOOP
# ---------------------------------------------------------
SCENARIOS = [
    {'id': 'S0', 'name': 'Normal Week',        'demand_mult': 1.0, 'time_mult': 1.0, 'shock_loc': None},
    {'id': 'S1', 'name': 'Peak Demand (+30%)', 'demand_mult': 1.3, 'time_mult': 1.0, 'shock_loc': None},
    {'id': 'S2a','name': 'Supply Shock — LOC_CH', 'demand_mult': 1.0, 'time_mult': 1.0, 'shock_loc': 'LOC_CH'},
    {'id': 'S2b','name': 'Supply Shock — LOC_BB', 'demand_mult': 1.0, 'time_mult': 1.0, 'shock_loc': 'LOC_BB'},
    {'id': 'S2c','name': 'Supply Shock — LOC_AH', 'demand_mult': 1.0, 'time_mult': 1.0, 'shock_loc': 'LOC_AH'},
]

print("\n2. Running AI Milk Run simulations...")

summary_rows       = []
master_routes_dict = {}  
master_spoilage_dict = {}

for sc in SCENARIOS:
    print(f"   -> {sc['id']}: {sc['name']}")
    sc_id     = sc['id']
    d_mult    = sc['demand_mult']
    t_mult    = sc['time_mult']
    shock_loc = sc['shock_loc']

    temp_demand = df_all_matches.groupby(['customer_id', 'sku_id'])['weekly_demand_mean_boxes'].first() * d_mult
    customer_demand = {k: int(math.ceil(v)) for k, v in temp_demand.items()}

    farm_inventory = {}
    for (farm, sku, loc), grp in df_all_matches.groupby(['farm_id', 'sku_id', 'location_id']):
        cap = grp['daily_capacity_boxes'].max()
        if shock_loc and loc == shock_loc:
            cap = cap * YIELD_SHOCK
        farm_inventory[(farm, sku)] = cap

    allocations = []
    for _, row in df_all_matches.iterrows():
        cust, sku, farm = row['customer_id'], row['sku_id'], row['farm_id']
        needed = customer_demand.get((cust, sku), 0)
        avail  = farm_inventory.get((farm, sku), 0)

        if needed <= 0 or avail <= 0: continue

        move = min(needed, avail)
        customer_demand[(cust, sku)] -= move
        farm_inventory[(farm, sku)]  -= move

        rec = row.copy()
        rec['allocated_boxes'] = move
        allocations.append(rec)

    df_plan = pd.DataFrame(allocations)

    sc_fuel_L, sc_fuel_cost, sc_total_cost = 0, 0, 0
    sc_trucks, sc_on_time, sc_dispatched, sc_spoiled = 0, 0, 0, 0

    # MAGIC HAPPENS HERE: Grouping by Farm + State + Cold Chain Rules
    for (farm, region_val, is_cold), group in df_plan.groupby(['farm_id', region_col, 'strict_cold_chain']):
        
        total_boxes = group['allocated_boxes'].sum()
        sc_dispatched += total_boxes
        
        farm_lat = group['farm_lat'].iloc[0]
        farm_lon = group['farm_lon'].iloc[0]
        route_dist_km = calculate_tsp_route(farm_lat, farm_lon, group)
        
        max_lead_time_route = group['max_lead_time_h'].min() 

        trucks = []
        if is_cold == 1:
            n = math.ceil(total_boxes / vehicles_dict['REEFER_TRK']['capacity_boxes'])
            trucks.extend(['REEFER_TRK'] * n)
        else:
            remaining = total_boxes
            while remaining > 0:
                if remaining > vehicles_dict['VAN_AMB']['capacity_boxes']:
                    trucks.append('LORRY_AMB')
                    remaining -= vehicles_dict['LORRY_AMB']['capacity_boxes']
                else:
                    trucks.append('VAN_AMB')
                    remaining -= vehicles_dict['VAN_AMB']['capacity_boxes']
        
        route_travel_h, route_fuel_L, route_fuel_cost, route_total_cost = 0, 0, 0, 0
        route_on_time = 1 

        for truck_id in trucks:
            v = vehicles_dict[truck_id]
            travel_h = (route_dist_km / v['avg_speed_kmph']) * t_mult
            fuel_l   = route_dist_km * v['fuel_l_per_km']
            fuel_rm  = fuel_l * FUEL_PRICE_RM
            total_rm = v['fixed_cost_per_trip_rm'] + fuel_rm + (route_dist_km * v['maintenance_rm_per_km'])
            
            sc_fuel_L     += fuel_l
            sc_fuel_cost  += fuel_rm
            sc_total_cost += total_rm
            sc_trucks     += 1
            if travel_h <= max_lead_time_route:
                sc_on_time += 1
            else:
                route_on_time = 0 
                
            route_travel_h = max(route_travel_h, travel_h)
            route_fuel_L     += fuel_l
            route_fuel_cost  += fuel_rm
            route_total_cost += total_rm

        key = (farm, region_val, "Cold" if is_cold else "Ambient")
        if key not in master_routes_dict:
            master_routes_dict[key] = {
                'Farm_ID': farm, 'Region_State': region_val, 'Fleet_Type': key[2],
                'Customers_Served': group['customer_id'].nunique(),
                'Strict_Lead_Time_h': max_lead_time_route
            }
            
        t_counts = Counter(trucks)
        master_routes_dict[key][f'Boxes_{sc_id}']     = total_boxes
        master_routes_dict[key][f'Trucks_{sc_id}']    = " + ".join([f"{v}x {k}" for k, v in t_counts.items()]) if trucks else "None"
        master_routes_dict[key][f'Dist_km_{sc_id}']   = round(route_dist_km, 2)
        master_routes_dict[key][f'Travel_h_{sc_id}']  = round(route_travel_h, 2)
        master_routes_dict[key][f'Cost_RM_{sc_id}']   = round(route_total_cost, 2)

        for _, row in group.iterrows():
            speed = (vehicles_dict['REEFER_TRK']['avg_speed_kmph'] if row['strict_cold_chain'] == 1 else vehicles_dict['LORRY_AMB']['avg_speed_kmph'])
            shelf_life = (row['shelf_life_cold_h'] if row['strict_cold_chain'] == 1 else row['shelf_life_ambient_h'])
            
            hours_over = max(0, route_travel_h - shelf_life)
            spoiled = min(row['allocated_boxes'], row['allocated_boxes'] * row['spoilage_rate_per_h_after_limit'] * hours_over)
            sc_spoiled += spoiled

            s_key = (farm, row['customer_id'], row['sku_id'])
            if s_key not in master_spoilage_dict:
                master_spoilage_dict[s_key] = {
                    'farm_id': farm, 'customer_id': row['customer_id'], 
                    'sku_id': row['sku_id'], 'sku_name': row['sku_name'],
                    'shelf_life_h': shelf_life
                }
            
            master_spoilage_dict[s_key][f'travel_h_{sc_id}'] = round(route_travel_h, 2)
            master_spoilage_dict[s_key][f'allocated_boxes_{sc_id}'] = row['allocated_boxes']
            master_spoilage_dict[s_key][f'spoiled_boxes_{sc_id}'] = round(spoiled, 2)

    on_time_pct  = (sc_on_time / sc_trucks * 100) if sc_trucks > 0 else 0
    discard_pct  = (sc_spoiled / sc_dispatched * 100) if sc_dispatched > 0 else 0

    summary_rows.append({
        'Scenario': sc['id'], 'Name': sc['name'], 'Shock Location': shock_loc if shock_loc else 'None',
        'Total Trucks': sc_trucks, 'Total Fuel (L)': round(sc_fuel_L, 1), 'Fuel Cost (RM)': round(sc_fuel_cost, 2),
        'Total Cost (RM)': round(sc_total_cost, 2), 'On-Time %': round(on_time_pct, 1),
        'Boxes Dispatched': round(sc_dispatched, 0), 'Spoiled Boxes': round(sc_spoiled, 1),
        'Discard Rate %': round(discard_pct, 4),
    })

# ---------------------------------------------------------
# 5. EXPORT DASHBOARDS WITH COLORS
# ---------------------------------------------------------
df_summary = pd.DataFrame(summary_rows)
df_summary.set_index('Scenario', inplace=True)
df_pivot = df_summary.T 

df_wide_routes = pd.DataFrame(list(master_routes_dict.values())).fillna(0)
df_wide_spoilage = pd.DataFrame(list(master_spoilage_dict.values())).fillna(0)

scenarios_ordered = ['S0', 'S1', 'S2a', 'S2b', 'S2c']

route_bases = ['Farm_ID', 'Region_State', 'Fleet_Type', 'Customers_Served', 'Strict_Lead_Time_h']
route_metrics = ['Boxes', 'Trucks', 'Dist_km', 'Travel_h', 'Cost_RM']
ordered_route_cols = route_bases.copy()
for sc in scenarios_ordered:
    for m in route_metrics:
        if f"{m}_{sc}" in df_wide_routes.columns:
            ordered_route_cols.append(f"{m}_{sc}")
df_wide_routes = df_wide_routes[ordered_route_cols]

spoil_bases = ['farm_id', 'customer_id', 'sku_id', 'sku_name', 'shelf_life_h']
spoil_metrics = ['travel_h', 'allocated_boxes', 'spoiled_boxes']
ordered_spoil_cols = spoil_bases.copy()
for sc in scenarios_ordered:
    for m in spoil_metrics:
        if f"{m}_{sc}" in df_wide_spoilage.columns:
            ordered_spoil_cols.append(f"{m}_{sc}")
df_wide_spoilage = df_wide_spoilage[ordered_spoil_cols]

# --- NEW: DATA DICTIONARY FOR PROPOSAL B ---
definitions = [
    {'Data Field': 'Farm_ID', 'Definition': 'The Farm ID supplying the vegetables.'},
    {'Data Field': 'Region_State', 'Definition': 'The consolidated geographic region (State/City) for this milk run.'},
    {'Data Field': 'Fleet_Type', 'Definition': 'Whether the route requires a REEFER (Cold) or LORRY/VAN (Ambient).'},
    {'Data Field': 'Customers_Served', 'Definition': 'The number of unique supermarkets sharing this single delivery route.'},
    {'Data Field': 'Strict_Lead_Time_h', 'Definition': 'The shortest (strictest) delivery deadline among all customers on this route.'},
    {'Data Field': 'Boxes_[S0/S1/S2]', 'Definition': 'Total boxes loaded into the consolidated fleet.'},
    {'Data Field': 'Trucks_[S0/S1/S2]', 'Definition': 'The aggregated list of vehicles deployed for this milk run.'},
    {'Data Field': 'Dist_km_[S0/S1/S2]', 'Definition': 'The TSP-calculated total driving distance to visit all stops on this route.'},
    {'Data Field': 'Travel_h_[S0/S1/S2]', 'Definition': 'The maximum travel time taken to complete all drop-offs.'},
    {'Data Field': 'Cost_RM_[S0/S1/S2]', 'Definition': 'The total Ringgit cost (Fixed + Fuel + Maintenance) for this shared route.'}
]
df_dict = pd.DataFrame(definitions)

# Save directly to the proposal B folder!
OUTPUT_FILE = os.path.join(script_dir, 'Step6_Proposal_B_MilkRun_Results.xlsx')
writer = pd.ExcelWriter(OUTPUT_FILE, engine='xlsxwriter')

df_pivot.to_excel(writer,       sheet_name='KPI_Comparison')
df_wide_routes.to_excel(writer, sheet_name='Wide_MilkRun_Routes', index=False)
df_wide_spoilage.to_excel(writer,sheet_name='Wide_Spoilage_Detail',  index=False)
df_dict.to_excel(writer,        sheet_name='Data_Dictionary', index=False)

workbook = writer.book
hdr_base = workbook.add_format({'bg_color': '#D9D9D9', 'bold': True, 'border': 1})
hdr_s0   = workbook.add_format({'bg_color': '#A9D08E', 'bold': True, 'border': 1})
hdr_s1   = workbook.add_format({'bg_color': '#9BC2E6', 'bold': True, 'border': 1})
hdr_s2a  = workbook.add_format({'bg_color': '#FFD966', 'bold': True, 'border': 1})
hdr_s2b  = workbook.add_format({'bg_color': '#F4B084', 'bold': True, 'border': 1})
hdr_s2c  = workbook.add_format({'bg_color': '#E699CC', 'bold': True, 'border': 1})

fmt_base = workbook.add_format({'bg_color': '#F2F2F2', 'border': 1})
fmt_s0   = workbook.add_format({'bg_color': '#E2EFDA', 'border': 1})
fmt_s1   = workbook.add_format({'bg_color': '#DDEBF7', 'border': 1})
fmt_s2a  = workbook.add_format({'bg_color': '#FFF2CC', 'border': 1})
fmt_s2b  = workbook.add_format({'bg_color': '#FCE4D6', 'border': 1})
fmt_s2c  = workbook.add_format({'bg_color': '#F4CCCC', 'border': 1})

def apply_pastel_colors(sheet_name, df):
    worksheet = writer.sheets[sheet_name]
    for col_num, col_name in enumerate(df.columns):
        if '_S0' in col_name:
            worksheet.write(0, col_num, col_name, hdr_s0) 
            worksheet.set_column(col_num, col_num, 16, fmt_s0) 
        elif '_S1' in col_name:
            worksheet.write(0, col_num, col_name, hdr_s1)
            worksheet.set_column(col_num, col_num, 16, fmt_s1)
        elif '_S2a' in col_name:
            worksheet.write(0, col_num, col_name, hdr_s2a)
            worksheet.set_column(col_num, col_num, 16, fmt_s2a)
        elif '_S2b' in col_name:
            worksheet.write(0, col_num, col_name, hdr_s2b)
            worksheet.set_column(col_num, col_num, 16, fmt_s2b)
        elif '_S2c' in col_name:
            worksheet.write(0, col_num, col_name, hdr_s2c)
            worksheet.set_column(col_num, col_num, 16, fmt_s2c)
        else:
            worksheet.write(0, col_num, col_name, hdr_base)
            worksheet.set_column(col_num, col_num, 16, fmt_base)

apply_pastel_colors('Wide_MilkRun_Routes', df_wide_routes)
apply_pastel_colors('Wide_Spoilage_Detail', df_wide_spoilage)

# Formatting the dictionary specifically so it looks clean
worksheet_dict = writer.sheets['Data_Dictionary']
worksheet_dict.set_column(0, 0, 25, fmt_base)
worksheet_dict.set_column(1, 1, 90, fmt_base)
worksheet_dict.write(0, 0, 'Data Field', hdr_base)
worksheet_dict.write(0, 1, 'Definition', hdr_base)

writer.close()
print(f"\nExported beautifully formatted dashboard to '{OUTPUT_FILE}'")
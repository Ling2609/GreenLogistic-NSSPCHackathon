import pandas as pd
import numpy as np
import math
import random
from collections import Counter

# ============================================================
# STEP 5 (PATCHED, WIDE, & COLOR-CODED) — PROPOSAL A PIPELINE
# ============================================================

FILE_NAME = 'Dataset_Preliminary_Presentation_v10 (1).xlsx'
FUEL_PRICE_RM = 2.05   
YIELD_SHOCK   = 0.8    

print("========================================")
print(" STEP 5: PROPOSAL A PIPELINE (COLOR DASHBOARD)")
print("========================================")

# ---------------------------------------------------------
# 1. LOAD ALL DATA
# ---------------------------------------------------------
print("\n1. Loading data...")
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

df_supply = pd.merge(df_farm_products, df_farms,    on='farm_id', how='left')
df_supply = pd.merge(df_supply,        df_products, on='sku_id',  how='left')
df_supply.rename(columns={'lat': 'farm_lat', 'lon': 'farm_lon'}, inplace=True)

df_demand_menu = pd.merge(df_demand, df_customers, on='customer_id', how='left')
df_demand_menu.rename(columns={'lat': 'cust_lat', 'lon': 'cust_lon'}, inplace=True)

vehicles_dict = df_vehicles.set_index('vehicle_type_id').to_dict('index')

# ---------------------------------------------------------
# 2. BUILD ALL POSSIBLE MATCHES WITH DISTANCES
# ---------------------------------------------------------
print("2. Building all possible farm-customer matches...")

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

def assign_trucks(cold_boxes, ambient_boxes):
    trucks = []
    reefer = vehicles_dict['REEFER_TRK']
    lorry  = vehicles_dict['LORRY_AMB']
    van    = vehicles_dict['VAN_AMB']

    if cold_boxes > 0:
        n = math.ceil(cold_boxes / reefer['capacity_boxes'])
        trucks.extend(['REEFER_TRK'] * n)
        spare = (n * reefer['capacity_boxes']) - cold_boxes
        ambient_boxes -= min(spare, ambient_boxes)  

    remaining = ambient_boxes
    while remaining > 0:
        if remaining > van['capacity_boxes']:
            trucks.append('LORRY_AMB')
            remaining -= lorry['capacity_boxes']
        else:
            trucks.append('VAN_AMB')
            remaining -= van['capacity_boxes']
    return trucks

def truck_kpis(truck_id, distance_km, time_mult, max_lead_h):
    v          = vehicles_dict[truck_id]
    travel_h   = (distance_km / v['avg_speed_kmph']) * time_mult
    fuel_L     = distance_km * v['fuel_l_per_km']
    fuel_cost  = fuel_L * FUEL_PRICE_RM
    maint_cost = distance_km * v['maintenance_rm_per_km']
    total_cost = v['fixed_cost_per_trip_rm'] + fuel_cost + maint_cost
    return {
        'travel_h':   travel_h,
        'fuel_L':     fuel_L,
        'fuel_cost':  fuel_cost,
        'total_cost': total_cost,
        'on_time':    1 if travel_h <= max_lead_h else 0,
    }

def calc_spoilage(boxes, distance_km, speed_kmph, time_mult, shelf_life_h, spoil_rate_per_h):
    travel_h   = (distance_km / speed_kmph) * time_mult
    hours_over = max(0, travel_h - shelf_life_h)
    spoiled    = min(boxes, boxes * spoil_rate_per_h * hours_over)
    return round(spoiled, 2)

# ---------------------------------------------------------
# 3. DEFINE SCENARIOS
# ---------------------------------------------------------
SCENARIOS = [
    {'id': 'S0', 'name': 'Normal Week',        'demand_mult': 1.0, 'time_mult': 1.0, 'shock_loc': None},
    {'id': 'S1', 'name': 'Peak Demand (+30%)', 'demand_mult': 1.3, 'time_mult': 1.0, 'shock_loc': None},
    {'id': 'S2a','name': 'Supply Shock — LOC_CH', 'demand_mult': 1.0, 'time_mult': 1.0, 'shock_loc': 'LOC_CH'},
    {'id': 'S2b','name': 'Supply Shock — LOC_BB', 'demand_mult': 1.0, 'time_mult': 1.0, 'shock_loc': 'LOC_BB'},
    {'id': 'S2c','name': 'Supply Shock — LOC_AH', 'demand_mult': 1.0, 'time_mult': 1.0, 'shock_loc': 'LOC_AH'},
]

# ---------------------------------------------------------
# 4. MAIN SCENARIO LOOP
# ---------------------------------------------------------
print("\n3. Running scenarios...")

summary_rows       = []
master_routes_dict = {}  
master_spoilage_dict = {} # NEW: Tracks wide dashboard columns for Spoilage

for sc in SCENARIOS:
    print(f"   -> {sc['id']}: {sc['name']}")
    sc_id     = sc['id']
    d_mult    = sc['demand_mult']
    t_mult    = sc['time_mult']
    shock_loc = sc['shock_loc']

    # ── PHASE A: CAPACITY-AWARE ALLOCATION ─────────────────
    customer_demand = (df_all_matches.groupby(['customer_id', 'sku_id'])['weekly_demand_mean_boxes'].first() * d_mult).to_dict()

    farm_inventory = {}
    for (farm, sku, loc), grp in df_all_matches.groupby(['farm_id', 'sku_id', 'location_id']):
        cap = grp['daily_capacity_boxes'].max()
        if shock_loc and loc == shock_loc:
            cap = cap * YIELD_SHOCK
        farm_inventory[(farm, sku)] = cap

    allocations = []
    for _, row in df_all_matches.iterrows():
        cust = row['customer_id']
        sku  = row['sku_id']
        farm = row['farm_id']

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

    # ── PHASE B: ROUTING, COSTS, SPOILAGE ──────────────────
    sc_fuel_L    = 0
    sc_fuel_cost = 0
    sc_total_cost= 0
    sc_trucks    = 0
    sc_on_time   = 0
    sc_dispatched= 0
    sc_spoiled   = 0

    for (farm, customer), group in df_plan.groupby(['farm_id', 'customer_id']):
        distance_km = group['distance_km'].iloc[0]
        max_lead_h  = group['max_lead_time_h'].iloc[0]

        cold_boxes    = group[group['strict_cold_chain'] == 1]['allocated_boxes'].sum()
        ambient_boxes = group[group['strict_cold_chain'] == 0]['allocated_boxes'].sum()
        sc_dispatched += cold_boxes + ambient_boxes

        trucks = assign_trucks(cold_boxes, ambient_boxes)
        
        route_travel_h   = 0
        route_fuel_L     = 0
        route_fuel_cost  = 0
        route_total_cost = 0
        route_on_time    = 1 

        for truck in trucks:
            kpis = truck_kpis(truck, distance_km, t_mult, max_lead_h)
            sc_fuel_L     += kpis['fuel_L']
            sc_fuel_cost  += kpis['fuel_cost']
            sc_total_cost += kpis['total_cost']
            sc_on_time    += kpis['on_time']
            sc_trucks     += 1
            
            if kpis['travel_h'] > route_travel_h: route_travel_h = kpis['travel_h'] 
            route_fuel_L     += kpis['fuel_L']
            route_fuel_cost  += kpis['fuel_cost']
            route_total_cost += kpis['total_cost']
            if kpis['on_time'] == 0: route_on_time = 0 

        # ── Dashboard Wide Logic (ROUTES) ─────────────────
        key = (farm, customer)
        if key not in master_routes_dict:
            master_routes_dict[key] = {
                'farm_id': farm, 'customer_id': customer,
                'distance_km': round(distance_km, 2), 'max_lead_time_h': max_lead_h
            }
            
        truck_counts = Counter(trucks)
        truck_str = " + ".join([f"{v}x {k}" for k, v in truck_counts.items()]) if trucks else "None"
        
        master_routes_dict[key][f'vehicle_type_{sc_id}']  = truck_str
        master_routes_dict[key][f'travel_time_h_{sc_id}'] = round(route_travel_h, 2)
        master_routes_dict[key][f'on_time_{sc_id}']       = route_on_time
        master_routes_dict[key][f'fuel_used_L_{sc_id}']   = round(route_fuel_L, 2)
        master_routes_dict[key][f'fuel_cost_RM_{sc_id}']  = round(route_fuel_cost, 2)
        master_routes_dict[key][f'total_cost_RM_{sc_id}'] = round(route_total_cost, 2)

        # ── Dashboard Wide Logic (SPOILAGE) ───────────────────────────
        for _, row in group.iterrows():
            speed = (vehicles_dict['REEFER_TRK']['avg_speed_kmph'] if row['strict_cold_chain'] == 1 else vehicles_dict['LORRY_AMB']['avg_speed_kmph'])
            shelf_life = (row['shelf_life_cold_h'] if row['strict_cold_chain'] == 1 else row['shelf_life_ambient_h'])
            spoiled = calc_spoilage(row['allocated_boxes'], distance_km, speed, t_mult, shelf_life, row['spoilage_rate_per_h_after_limit'])
            sc_spoiled += spoiled

            # Wide format for Spoilage!
            s_key = (farm, customer, row['sku_id'])
            if s_key not in master_spoilage_dict:
                master_spoilage_dict[s_key] = {
                    'farm_id': farm, 'customer_id': customer, 
                    'sku_id': row['sku_id'], 'sku_name': row['sku_name'],
                    'distance_km': round(distance_km, 2), 'shelf_life_h': shelf_life
                }
            
            master_spoilage_dict[s_key][f'travel_h_{sc_id}'] = round(distance_km / speed * t_mult, 2)
            master_spoilage_dict[s_key][f'allocated_boxes_{sc_id}'] = row['allocated_boxes']
            master_spoilage_dict[s_key][f'spoiled_boxes_{sc_id}'] = spoiled

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
# 5. PRINT & EXPORT WITH EXCEL COLOR STYLING
# ---------------------------------------------------------
df_summary = pd.DataFrame(summary_rows)
df_summary.set_index('Scenario', inplace=True)
df_pivot = df_summary.T 

df_wide_routes = pd.DataFrame(list(master_routes_dict.values())).fillna(0)
df_wide_spoilage = pd.DataFrame(list(master_spoilage_dict.values())).fillna(0)

# Generate Data Dictionary
definitions = [
    {'Data Field': 'farm_id', 'Definition': 'The Farm ID supplying the vegetables.'},
    {'Data Field': 'customer_id', 'Definition': 'The Customer ID receiving the vegetables.'},
    {'Data Field': 'distance_km', 'Definition': 'The one-way road distance estimated with circuity multiplier.'},
    {'Data Field': 'max_lead_time_h', 'Definition': 'The strict delivery deadline set by the customer.'},
    {'Data Field': 'vehicle_type_[S0/S1/S2]', 'Definition': 'The aggregated list of vehicles deployed for this route during that specific scenario.'},
    {'Data Field': 'travel_time_h_[S0/S1/S2]', 'Definition': 'The maximum travel time taken by the trucks on this route.'},
    {'Data Field': 'on_time_[S0/S1/S2]', 'Definition': '1 if all trucks on the route arrived within the lead time, 0 if late.'},
    {'Data Field': 'fuel_used_L_[S0/S1/S2]', 'Definition': 'The sum of fuel consumed by all trucks on this route.'},
    {'Data Field': 'fuel_cost_RM_[S0/S1/S2]', 'Definition': 'The total fuel cost for this route (Fuel L * RM 2.05).'},
    {'Data Field': 'total_cost_RM_[S0/S1/S2]', 'Definition': 'The total Ringgit cost (Fixed + Fuel + Maintenance) for this route.'}
]
df_dict = pd.DataFrame(definitions)

print("\n" + "=" * 75)
print("         PROPOSAL A — KPI DASHBOARD (SIDE-BY-SIDE)")
print("=" * 75)
print(df_pivot.to_string())
print("=" * 75)

# Initialize the XlsxWriter engine to enable Pastel Coloring
OUTPUT_FILE = 'Step5_Master_Scenario_Results_Patched.xlsx'
writer = pd.ExcelWriter(OUTPUT_FILE, engine='xlsxwriter')

df_pivot.to_excel(writer,       sheet_name='KPI_Comparison')
df_wide_routes.to_excel(writer, sheet_name='Wide_Route_Comparison', index=False)
df_wide_spoilage.to_excel(writer,sheet_name='Wide_Spoilage_Detail',  index=False)
df_dict.to_excel(writer,        sheet_name='Data_Dictionary', index=False)

# Get the workbook object to add formats
workbook = writer.book

# Define Pastel Color Formats
fmt_base = workbook.add_format({'bg_color': '#F2F2F2', 'border': 1}) # Light Grey (Base Info)
fmt_s0   = workbook.add_format({'bg_color': '#E2EFDA', 'border': 1}) # Pastel Green (Normal)
fmt_s1   = workbook.add_format({'bg_color': '#DDEBF7', 'border': 1}) # Pastel Blue (Spike)
fmt_s2a  = workbook.add_format({'bg_color': '#FFF2CC', 'border': 1}) # Pastel Yellow (Shock CH)
fmt_s2b  = workbook.add_format({'bg_color': '#FCE4D6', 'border': 1}) # Pastel Orange (Shock BB)
fmt_s2c  = workbook.add_format({'bg_color': '#F4CCCC', 'border': 1}) # Pastel Red (Shock AH)

def apply_pastel_colors(sheet_name, df):
    worksheet = writer.sheets[sheet_name]
    for col_num, col_name in enumerate(df.columns):
        # Set default width
        worksheet.set_column(col_num, col_num, 16)
        
        # Apply the color based on the column name!
        if '_S0' in col_name:
            worksheet.set_column(col_num, col_num, 16, fmt_s0)
        elif '_S1' in col_name:
            worksheet.set_column(col_num, col_num, 16, fmt_s1)
        elif '_S2a' in col_name:
            worksheet.set_column(col_num, col_num, 16, fmt_s2a)
        elif '_S2b' in col_name:
            worksheet.set_column(col_num, col_num, 16, fmt_s2b)
        elif '_S2c' in col_name:
            worksheet.set_column(col_num, col_num, 16, fmt_s2c)
        else:
            worksheet.set_column(col_num, col_num, 14, fmt_base)

# Apply the coloring logic to the two wide sheets
apply_pastel_colors('Wide_Route_Comparison', df_wide_routes)
apply_pastel_colors('Wide_Spoilage_Detail', df_wide_spoilage)

writer.close()
print(f"\nExported beautifully formatted dashboard to '{OUTPUT_FILE}'")
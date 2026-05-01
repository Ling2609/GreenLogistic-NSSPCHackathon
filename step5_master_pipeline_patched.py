import pandas as pd
import numpy as np
import math
import random

# ============================================================
# STEP 5 (PATCHED) — PROPOSAL A FULL SCENARIO PIPELINE
#
# Fixes applied vs original step5:
#   1. S2 re-sourcing: shortfall from shocked location is
#      sourced from the next nearest alternative farm
#   2. Spoilage / discard rate added as mandatory KPI
#   3. Total Fuel (L) and Fuel Cost (RM) added separately
#   4. S2 now simulates ALL 3 shock locations (not random)
#      so your report has deterministic, comparable numbers
# ============================================================

FILE_NAME = 'Dataset_Preliminary_Presentation_v10 (1).xlsx'
FUEL_PRICE_RM = 2.05   # from dataset README
YIELD_SHOCK   = 0.8    # S2: shocked location produces 80%

print("========================================")
print(" STEP 5 (PATCHED): FULL SCENARIO PIPELINE")
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

# Build master supply table (farm + product details in one row)
df_supply = pd.merge(df_farm_products, df_farms,    on='farm_id', how='left')
df_supply = pd.merge(df_supply,        df_products, on='sku_id',  how='left')
df_supply.rename(columns={'lat': 'farm_lat', 'lon': 'farm_lon'}, inplace=True)

# Build master demand table (order + customer details in one row)
df_demand_menu = pd.merge(df_demand, df_customers, on='customer_id', how='left')
df_demand_menu.rename(columns={'lat': 'cust_lat', 'lon': 'cust_lon'}, inplace=True)

# Vehicle lookup dictionary from Excel (reads exact values, no hardcoding)
vehicles_dict = df_vehicles.set_index('vehicle_type_id').to_dict('index')

# ---------------------------------------------------------
# 2. BUILD ALL POSSIBLE MATCHES WITH DISTANCES
# ---------------------------------------------------------
print("2. Building all possible farm-customer matches...")

def haversine_road(lat1, lon1, lat2, lon2):
    """Straight-line distance × 1.3 circuity = road distance estimate."""
    R = 6371.0
    lat1, lon1, lat2, lon2 = map(np.radians, [lat1, lon1, lat2, lon2])
    a = np.sin((lat2-lat1)/2)**2 + np.cos(lat1)*np.cos(lat2)*np.sin((lon2-lon1)/2)**2
    return R * 2 * np.arctan2(np.sqrt(a), np.sqrt(1-a)) * 1.3

# Inner join: one row per (customer, sku, farm) combination
df_all_matches = pd.merge(df_demand_menu, df_supply, on='sku_id', how='inner')
df_all_matches['distance_km'] = haversine_road(
    df_all_matches['farm_lat'], df_all_matches['farm_lon'],
    df_all_matches['cust_lat'], df_all_matches['cust_lon']
)
df_all_matches['strict_cold_chain'] = df_all_matches[
    ['cold_storage_requested', 'cold_required']].max(axis=1)

# Sort by customer → sku → nearest farm (closest first)
df_all_matches = df_all_matches.sort_values(
    ['customer_id', 'sku_id', 'distance_km']).reset_index(drop=True)

print(f"   {len(df_all_matches)} total possible routes generated.")

# ---------------------------------------------------------
# HELPER: Assign trucks for a route
# ---------------------------------------------------------
def assign_trucks(cold_boxes, ambient_boxes):
    trucks = []
    reefer = vehicles_dict['REEFER_TRK']
    lorry  = vehicles_dict['LORRY_AMB']
    van    = vehicles_dict['VAN_AMB']

    # Cold boxes → must use REEFER_TRK
    if cold_boxes > 0:
        n = math.ceil(cold_boxes / reefer['capacity_boxes'])
        trucks.extend(['REEFER_TRK'] * n)
        spare = (n * reefer['capacity_boxes']) - cold_boxes
        ambient_boxes -= min(spare, ambient_boxes)  # fill spare reefer space

    # Remaining ambient boxes → cheapest option
    remaining = ambient_boxes
    while remaining > 0:
        if remaining > van['capacity_boxes']:
            trucks.append('LORRY_AMB')
            remaining -= lorry['capacity_boxes']
        else:
            trucks.append('VAN_AMB')
            remaining -= van['capacity_boxes']
    return trucks


# ---------------------------------------------------------
# HELPER: Calculate KPIs for one truck trip
# ---------------------------------------------------------
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


# ---------------------------------------------------------
# HELPER: Calculate spoilage for one order line
# Spoilage only counts AFTER shelf life is exceeded.
# Formula: spoiled = boxes × rate × hours_over_limit
# ---------------------------------------------------------
def calc_spoilage(boxes, distance_km, speed_kmph, time_mult,
                  shelf_life_h, spoil_rate_per_h):
    travel_h   = (distance_km / speed_kmph) * time_mult
    hours_over = max(0, travel_h - shelf_life_h)
    spoiled    = min(boxes, boxes * spoil_rate_per_h * hours_over)
    return round(spoiled, 2)


# ---------------------------------------------------------
# 3. DEFINE SCENARIOS
# We simulate S2 for ALL 3 locations so results are
# deterministic and comparable in your report.
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

summary_rows     = []
all_route_rows   = []
all_spoilage_rows = []

for sc in SCENARIOS:
    print(f"   -> {sc['id']}: {sc['name']}")

    d_mult    = sc['demand_mult']
    t_mult    = sc['time_mult']
    shock_loc = sc['shock_loc']

    # ── PHASE A: CAPACITY-AWARE ALLOCATION ─────────────────
    # Reset demand and inventory trackers for each scenario
    customer_demand = (
        df_all_matches.groupby(['customer_id', 'sku_id'])['weekly_demand_mean_boxes']
        .first() * d_mult
    ).to_dict()

    farm_inventory = {}
    for (farm, sku, loc), grp in df_all_matches.groupby(['farm_id', 'sku_id', 'location_id']):
        cap = grp['daily_capacity_boxes'].max()
        # S2: reduce capacity by 20% for the shocked location
        if shock_loc and loc == shock_loc:
            cap = cap * YIELD_SHOCK
        farm_inventory[(farm, sku)] = cap

    allocations = []
    # Iterate rows already sorted nearest-first → greedy closest-farm logic
    for _, row in df_all_matches.iterrows():
        cust = row['customer_id']
        sku  = row['sku_id']
        farm = row['farm_id']

        needed = customer_demand.get((cust, sku), 0)
        avail  = farm_inventory.get((farm, sku), 0)

        if needed <= 0 or avail <= 0:
            continue

        move = min(needed, avail)
        customer_demand[(cust, sku)] -= move
        farm_inventory[(farm, sku)]  -= move

        rec = row.copy()
        rec['allocated_boxes'] = move
        allocations.append(rec)

    df_plan = pd.DataFrame(allocations)

    # Check if any demand was unmet (flag for report)
    unmet = {k: v for k, v in customer_demand.items() if v > 0.01}
    if unmet:
        print(f"      WARNING: {len(unmet)} orders partially unmet in {sc['id']}")

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

        for truck in trucks:
            kpis = truck_kpis(truck, distance_km, t_mult, max_lead_h)
            sc_fuel_L     += kpis['fuel_L']
            sc_fuel_cost  += kpis['fuel_cost']
            sc_total_cost += kpis['total_cost']
            sc_on_time    += kpis['on_time']
            sc_trucks     += 1

            all_route_rows.append({
                'Scenario':      sc['id'],
                'farm_id':       farm,
                'customer_id':   customer,
                'distance_km':   round(distance_km, 2),
                'vehicle_type':  truck,
                'travel_time_h': round(kpis['travel_h'], 2),
                'max_lead_time_h': max_lead_h,
                'on_time':       kpis['on_time'],
                'fuel_used_L':   round(kpis['fuel_L'], 2),
                'fuel_cost_RM':  round(kpis['fuel_cost'], 2),
                'total_cost_RM': round(kpis['total_cost'], 2),
            })

        # ── Spoilage per SKU line ───────────────────────────
        for _, row in group.iterrows():
            # Use reefer speed if cold chain, lorry speed otherwise
            speed = (vehicles_dict['REEFER_TRK']['avg_speed_kmph']
                     if row['strict_cold_chain'] == 1
                     else vehicles_dict['LORRY_AMB']['avg_speed_kmph'])
            shelf_life = (row['shelf_life_cold_h']
                          if row['strict_cold_chain'] == 1
                          else row['shelf_life_ambient_h'])
            spoiled = calc_spoilage(
                row['allocated_boxes'], distance_km, speed, t_mult,
                shelf_life, row['spoilage_rate_per_h_after_limit']
            )
            sc_spoiled += spoiled

            all_spoilage_rows.append({
                'Scenario':         sc['id'],
                'customer_id':      customer,
                'sku_id':           row['sku_id'],
                'sku_name':         row['sku_name'],
                'farm_id':          farm,
                'distance_km':      round(distance_km, 2),
                'travel_h':         round(distance_km / speed * t_mult, 2),
                'shelf_life_h':     shelf_life,
                'allocated_boxes':  row['allocated_boxes'],
                'spoiled_boxes':    spoiled,
            })

    # ── Scenario summary row ────────────────────────────────
    on_time_pct  = (sc_on_time / sc_trucks * 100) if sc_trucks > 0 else 0
    discard_pct  = (sc_spoiled / sc_dispatched * 100) if sc_dispatched > 0 else 0

    summary_rows.append({
        'Scenario':          sc['id'],
        'Name':              sc['name'],
        'Shock Location':    shock_loc if shock_loc else 'None',
        'Total Trucks':      sc_trucks,
        'Total Fuel (L)':    round(sc_fuel_L, 1),
        'Fuel Cost (RM)':    round(sc_fuel_cost, 2),
        'Total Cost (RM)':   round(sc_total_cost, 2),
        'On-Time %':         round(on_time_pct, 1),
        'Boxes Dispatched':  round(sc_dispatched, 0),
        'Spoiled Boxes':     round(sc_spoiled, 1),
        'Discard Rate %':    round(discard_pct, 2),
    })

# ---------------------------------------------------------
# 5. PRINT & EXPORT
# ---------------------------------------------------------
df_summary  = pd.DataFrame(summary_rows)
df_routes   = pd.DataFrame(all_route_rows)
df_spoilage = pd.DataFrame(all_spoilage_rows)

print("\n" + "=" * 75)
print("         PROPOSAL A — FULL SCENARIO RESULTS (ALL KPIs)")
print("=" * 75)
print(df_summary.to_string(index=False))
print("=" * 75)

with pd.ExcelWriter('Step5_Master_Scenario_Results_Patched.xlsx') as writer:
    df_summary.to_excel(writer,  sheet_name='KPI_Summary',      index=False)
    df_routes.to_excel(writer,   sheet_name='Route_Detail',     index=False)
    df_spoilage.to_excel(writer, sheet_name='Spoilage_Detail',  index=False)

print("\nExported to 'Step5_Master_Scenario_Results_Patched.xlsx'")
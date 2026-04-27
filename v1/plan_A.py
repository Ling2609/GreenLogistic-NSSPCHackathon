import pandas as pd
import numpy as np
import math

# ============================================================
# PROPOSAL A — FULL SCENARIO SIMULATION (S0, S1, S2a/b/c)
#
# S0: Normal baseline
# S1: Peak Demand — all customer demand x1.3
# S2: Supply Shock — ONE location yields -20% (randomized)
#     We simulate ALL 3 possibilities:
#       S2a = LOC_CH (Cameron Highlands) shocked
#       S2b = LOC_BB (Batang Berjuntai) shocked
#       S2c = LOC_AH (Air Hitam) shocked
#     For each shock: shortfall is re-sourced from the
#     next nearest farm that grows the same SKU.
# ============================================================

FUEL_PRICE_RM_PER_L = 2.05  # from dataset README

VEHICLES = {
    'REEFER_TRK': {
        'cap': 400, 'cold_capable': True,
        'fixed_cost': 450,  'fuel_l_per_km': 0.38,
        'maintenance_rm_per_km': 0.36, 'avg_speed_kmph': 48
    },
    'LORRY_AMB': {
        'cap': 500, 'cold_capable': False,
        'fixed_cost': 280,  'fuel_l_per_km': 0.32,
        'maintenance_rm_per_km': 0.30, 'avg_speed_kmph': 50
    },
    'VAN_AMB': {
        'cap': 120, 'cold_capable': False,
        'fixed_cost': 120,  'fuel_l_per_km': 0.12,
        'maintenance_rm_per_km': 0.22, 'avg_speed_kmph': 55
    },
}

# ── All scenarios including 3 versions of S2 ────────────────
SCENARIOS = {
    'S0_Normal':      {'demand_mult': 1.0, 'time_mult': 1.0, 'shock_loc': None},
    'S1_Peak_Demand': {'demand_mult': 1.3, 'time_mult': 1.0, 'shock_loc': None},
    'S2a_Shock_CH':   {'demand_mult': 1.0, 'time_mult': 1.0, 'shock_loc': 'LOC_CH'},
    'S2b_Shock_BB':   {'demand_mult': 1.0, 'time_mult': 1.0, 'shock_loc': 'LOC_BB'},
    'S2c_Shock_AH':   {'demand_mult': 1.0, 'time_mult': 1.0, 'shock_loc': 'LOC_AH'},
}

YIELD_SHOCK = 0.8  # shocked location produces only 80%


# ============================================================
# HELPER: Haversine distance between two lat/lon points
# ============================================================
def haversine(lat1, lon1, lat2, lon2):
    R = 6371.0
    lat1, lon1, lat2, lon2 = map(np.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = np.sin(dlat/2)**2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon/2)**2
    return R * 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))


# ============================================================
# HELPER: Assign trucks for a route
# ============================================================
def assign_vehicles(cold_boxes, ambient_boxes):
    trucks = []
    if cold_boxes > 0:
        num_reefers = math.ceil(cold_boxes / VEHICLES['REEFER_TRK']['cap'])
        trucks.extend(['REEFER_TRK'] * num_reefers)
        spare = (num_reefers * VEHICLES['REEFER_TRK']['cap']) - cold_boxes
        ambient_boxes -= min(spare, ambient_boxes)

    remaining = ambient_boxes
    while remaining > 0:
        if remaining > VEHICLES['VAN_AMB']['cap']:
            trucks.append('LORRY_AMB')
            remaining -= VEHICLES['LORRY_AMB']['cap']
        else:
            trucks.append('VAN_AMB')
            remaining -= VEHICLES['VAN_AMB']['cap']
    return trucks


# ============================================================
# HELPER: Calculate trip KPIs for one truck
# ============================================================
def trip_kpis(truck, distance_km, travel_h, max_lead_h):
    v = VEHICLES[truck]
    fuel_L        = distance_km * v['fuel_l_per_km']
    fuel_cost     = fuel_L * FUEL_PRICE_RM_PER_L
    maint_cost    = distance_km * v['maintenance_rm_per_km']
    total_cost    = v['fixed_cost'] + fuel_cost + maint_cost
    return {
        'fuel_used_L':   round(fuel_L, 2),
        'fuel_cost_RM':  round(fuel_cost, 2),
        'total_cost_RM': round(total_cost, 2),
        'on_time':       1 if travel_h <= max_lead_h else 0,
    }


# ============================================================
# HELPER: Calculate spoilage for one order line
# Each SKU has its own spoilage_rate_per_h_after_limit
# Spoilage only starts AFTER shelf life is exceeded
# ============================================================
def calc_spoilage(boxes, travel_h, shelf_life_h, spoil_rate_per_h):
    hours_over    = max(0, travel_h - shelf_life_h)
    spoiled_boxes = min(boxes, boxes * spoil_rate_per_h * hours_over)
    return round(spoiled_boxes, 2)


# ============================================================
# LOAD DATA
# ============================================================
print("Loading data...")
df_plan    = pd.read_excel('Phase_A_Fulfillment_Plan.xlsx')
df_routes_all = pd.read_excel('Master_Route_Options.xlsx')

# Clean keys for safe merging
for col in ['customer_id', 'sku_id', 'farm_id']:
    if col in df_routes_all.columns:
        df_routes_all[col] = df_routes_all[col].astype(str).str.strip().str.upper()

print(f"Loaded {len(df_plan)} order lines from Proposal A plan.")
print(f"Loaded {len(df_routes_all)} possible routes from Master_Route_Options.\n")

# Derive location_id from farm_name since Master_Route_Options doesn't have it
def get_location(farm_name):
    name = str(farm_name).lower()
    if 'cameron' in name: return 'LOC_CH'
    if 'batang'  in name: return 'LOC_BB'
    if 'air'     in name: return 'LOC_AH'
    return 'UNKNOWN'

df_routes_all['location_id'] = df_routes_all['farm_name'].apply(get_location)

# Add real_road_distance_km (1.3x haversine) if not present
if 'real_road_distance_km' not in df_routes_all.columns:
    df_routes_all['real_road_distance_km'] = df_routes_all['distance_km'] * 1.3

# ============================================================
# MAIN SIMULATION
# ============================================================
all_route_rows    = []
all_spoilage_rows = []
summary_rows      = []

for scenario_name, cfg in SCENARIOS.items():
    print(f"Simulating {scenario_name}...")

    demand_mult = cfg['demand_mult']
    time_mult   = cfg['time_mult']
    shock_loc   = cfg['shock_loc']   # None for S0/S1, a location for S2

    route_rows    = []
    spoilage_rows = []

    for (farm, customer), group in df_plan.groupby(['farm_id', 'customer_id']):

        location_id = group['location_id'].iloc[0]
        distance_km = group['real_road_distance_km'].iloc[0]
        max_lead_h  = group['max_lead_time_h'].iloc[0]
        cust_lat    = group['cust_lat'].iloc[0]
        cust_lon    = group['cust_lon'].iloc[0]

        # ── Determine supply factor for this farm ────────────
        # If this farm's location is shocked, it produces only 80%
        supply_factor = YIELD_SHOCK if (shock_loc and location_id == shock_loc) else 1.0

        # ── Per SKU: handle shortfall if supply is reduced ───
        for _, row in group.iterrows():
            sku            = row['sku_id']
            total_demand   = row['weekly_demand_mean_boxes'] * demand_mult
            primary_supply = total_demand * supply_factor
            shortfall      = total_demand - primary_supply  # 0 if no shock

            # Primary delivery (from original assigned farm)
            deliveries = [{'distance_km': distance_km, 'boxes': primary_supply,
                           'farm_id': farm, 'source': 'primary'}]

            # ── Re-source the shortfall from next best farm ──
            if shortfall > 0:
                # Find all OTHER farms that grow this SKU,
                # NOT in the shocked location, sorted by distance to customer
                alternatives = df_routes_all[
                    (df_routes_all['sku_id'] == sku) &
                    (df_routes_all['customer_id'] == customer) &
                    (df_routes_all['farm_id'] != farm) &
                    (df_routes_all['location_id'] != shock_loc)
                ].sort_values('distance_km')

                if len(alternatives) > 0:
                    alt = alternatives.iloc[0]
                    alt_distance = alt['real_road_distance_km'] if 'real_road_distance_km' in alt else alt['distance_km'] * 1.3
                    deliveries.append({
                        'distance_km': alt_distance,
                        'boxes': shortfall,
                        'farm_id': alt['farm_id'],
                        'source': 'resourced'
                    })
                else:
                    # No alternative farm found — flag it
                    print(f"  WARNING: No alternative farm for {sku} → {customer}. Shortfall unmet.")

            # ── Calculate spoilage per delivery leg ──────────
            for delivery in deliveries:
                speed     = (VEHICLES['REEFER_TRK']['avg_speed_kmph']
                             if row['strict_cold_chain'] == 1
                             else VEHICLES['LORRY_AMB']['avg_speed_kmph'])
                travel_h  = (delivery['distance_km'] / speed) * time_mult
                shelf_life = (row['shelf_life_cold_h']
                              if row['strict_cold_chain'] == 1
                              else row['shelf_life_ambient_h'])
                spoiled = calc_spoilage(
                    delivery['boxes'], travel_h,
                    shelf_life, row['spoilage_rate_per_h_after_limit']
                )
                spoilage_rows.append({
                    'Scenario':         scenario_name,
                    'customer_id':      customer,
                    'sku_id':           sku,
                    'sku_name':         row['sku_name'],
                    'farm_id':          delivery['farm_id'],
                    'source':           delivery['source'],
                    'distance_km':      round(delivery['distance_km'], 2),
                    'travel_h':         round(travel_h, 2),
                    'shelf_life_h':     shelf_life,
                    'dispatched_boxes': round(delivery['boxes'], 1),
                    'spoiled_boxes':    spoiled,
                })

        # ── Vehicle assignment for the full route ────────────
        # Use total demand (after demand_mult) for truck sizing
        cold_boxes    = group[group['strict_cold_chain'] == 1]['weekly_demand_mean_boxes'].sum() * demand_mult * supply_factor
        ambient_boxes = group[group['strict_cold_chain'] == 0]['weekly_demand_mean_boxes'].sum() * demand_mult * supply_factor
        trucks        = assign_vehicles(cold_boxes, ambient_boxes)

        for truck in trucks:
            travel_h = (distance_km / VEHICLES[truck]['avg_speed_kmph']) * time_mult
            kpis     = trip_kpis(truck, distance_km, travel_h, max_lead_h)
            route_rows.append({
                'Scenario':        scenario_name,
                'farm_id':         farm,
                'customer_id':     customer,
                'location_id':     location_id,
                'distance_km':     round(distance_km, 2),
                'vehicle_type':    truck,
                'travel_time_h':   round(travel_h, 2),
                'max_lead_time_h': max_lead_h,
                **kpis
            })

    # ── Scenario Summary ─────────────────────────────────────
    df_r = pd.DataFrame(route_rows)
    df_s = pd.DataFrame(spoilage_rows)

    total_trucks     = len(df_r)
    on_time_count    = df_r['on_time'].sum()
    total_dispatched = df_s['dispatched_boxes'].sum()
    total_spoiled    = df_s['spoiled_boxes'].sum()

    summary_rows.append({
        'Scenario':         scenario_name,
        'Shock Location':   shock_loc if shock_loc else 'None',
        'Total Trucks':     total_trucks,
        'Total Fuel (L)':   round(df_r['fuel_used_L'].sum(), 1),
        'Fuel Cost (RM)':   round(df_r['fuel_cost_RM'].sum(), 2),
        'Total Cost (RM)':  round(df_r['total_cost_RM'].sum(), 2),
        'On-Time %':        round((on_time_count / total_trucks) * 100, 1),
        'Dispatched Boxes': round(total_dispatched, 0),
        'Spoiled Boxes':    round(total_spoiled, 1),
        'Discard Rate %':   round((total_spoiled / total_dispatched) * 100, 2) if total_dispatched > 0 else 0,
    })

    all_route_rows.extend(route_rows)
    all_spoilage_rows.extend(spoilage_rows)

# ============================================================
# PRINT & EXPORT
# ============================================================
df_summary  = pd.DataFrame(summary_rows)
df_routes   = pd.DataFrame(all_route_rows)
df_spoilage = pd.DataFrame(all_spoilage_rows)

print("\n" + "=" * 80)
print("         PROPOSAL A — FULL SCENARIO RESULTS")
print("=" * 80)
print(df_summary.to_string(index=False))
print("=" * 80)

with pd.ExcelWriter('Proposal_A_Full_Scenarios.xlsx') as writer:
    df_summary.to_excel(writer,  sheet_name='Summary',          index=False)
    df_routes.to_excel(writer,   sheet_name='Route_Detail',     index=False)
    df_spoilage.to_excel(writer, sheet_name='Spoilage_Detail',  index=False)

print("\nExported to 'Proposal_A_Full_Scenarios.xlsx'")
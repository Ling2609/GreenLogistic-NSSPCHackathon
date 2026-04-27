import pandas as pd
import math
import random

# ============================================================
# PROPOSAL A — SCENARIO SIMULATION (S0, S1, S2)
# Using EXACT values from Dataset_Preliminary_Presentation
# ============================================================

FUEL_PRICE_RM_PER_L = 2.05  # from dataset README

# ── VEHICLE SPECS (from Vehicles sheet — exact values) ──────
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

# ── SCENARIOS (from Scenarios sheet — exact values) ─────────
# S0: Normal baseline
# S1: Peak Demand — all customer demand +30% (multiplier = 1.3)
# S2: Supply Shock — yield -20% in ONE location (randomized)
#     NOTE: travel_time_multiplier = 1 for ALL scenarios
#     NOTE: there is NO spoilage multiplier in this dataset

SCENARIOS = {
    'S0_Normal':      {'demand_mult': 1.0, 'time_mult': 1.0},
    'S1_Peak_Demand': {'demand_mult': 1.3, 'time_mult': 1.0},
    'S2_Supply_Shock':{'demand_mult': 1.0, 'time_mult': 1.0},
}

# S2: one random location gets yield_multiplier = 0.8 (20% less supply)
# We pick randomly as the brief says "randomized"
S2_SHOCK_LOCATION = random.choice(['LOC_CH', 'LOC_BB', 'LOC_AH'])
S2_YIELD_MULT     = 0.8
print(f"S2 Supply Shock will hit: {S2_SHOCK_LOCATION} (yield x{S2_YIELD_MULT})")


# ============================================================
# HELPER: Pick vehicles for one farm→customer route
# ============================================================
def assign_vehicles(cold_boxes, ambient_boxes):
    trucks = []

    # Cold boxes MUST use REEFER_TRK (hard constraint)
    if cold_boxes > 0:
        num_reefers = math.ceil(cold_boxes / VEHICLES['REEFER_TRK']['cap'])
        trucks.extend(['REEFER_TRK'] * num_reefers)
        # Fill spare reefer space with ambient boxes (efficiency)
        spare = (num_reefers * VEHICLES['REEFER_TRK']['cap']) - cold_boxes
        ambient_boxes -= min(spare, ambient_boxes)

    # Remaining ambient boxes use cheaper lorry or van
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
# HELPER: Calculate KPIs for one truck trip
# Total Cost formula (from problem brief):
#   = fixed_cost + (fuel_l_per_km x FUEL_PRICE + maintenance) x distance
# ============================================================
def calculate_trip_kpis(truck, distance_km, travel_time_h, max_lead_h):
    v             = VEHICLES[truck]
    fuel_used_L   = distance_km * v['fuel_l_per_km']
    fuel_cost_RM  = fuel_used_L * FUEL_PRICE_RM_PER_L
    maint_cost_RM = distance_km * v['maintenance_rm_per_km']
    total_cost_RM = v['fixed_cost'] + fuel_cost_RM + maint_cost_RM
    on_time       = 1 if travel_time_h <= max_lead_h else 0

    return {
        'fuel_used_L':   round(fuel_used_L, 2),
        'fuel_cost_RM':  round(fuel_cost_RM, 2),
        'total_cost_RM': round(total_cost_RM, 2),
        'on_time':       on_time,
    }


# ============================================================
# HELPER: Calculate spoilage for one order line
# Only counts AFTER shelf life is exceeded (per brief rules)
# ============================================================
def calculate_spoilage(row, travel_time_h, dispatched_boxes):
    shelf_life = (row['shelf_life_cold_h']
                  if row['strict_cold_chain'] == 1
                  else row['shelf_life_ambient_h'])
    spoil_rate    = row['spoilage_rate_per_h_after_limit']
    hours_over    = max(0, travel_time_h - shelf_life)
    spoiled_boxes = min(dispatched_boxes, dispatched_boxes * spoil_rate * hours_over)
    return round(spoiled_boxes, 2)


# ============================================================
# LOAD DATA
# ============================================================
print("\nLoading data...")
df = pd.read_excel('Phase_A_Fulfillment_Plan.xlsx')
print(f"Loaded {len(df)} order lines.")

all_route_rows    = []
all_spoilage_rows = []
summary_rows      = []

# ============================================================
# MAIN SIMULATION LOOP
# ============================================================
for scenario_name, mult in SCENARIOS.items():
    print(f"\nSimulating {scenario_name}...")
    route_rows    = []
    spoilage_rows = []

    for (farm, customer), group in df.groupby(['farm_id', 'customer_id']):
        distance_km = group['real_road_distance_km'].iloc[0]
        max_lead_h  = group['max_lead_time_h'].iloc[0]
        location_id = group['location_id'].iloc[0]

        # ── Apply demand multiplier ──────────────────────────
        demand_mult = mult['demand_mult']

        # ── S2: Reduce supply from shocked location by 20% ──
        # If this farm is in the shocked location,
        # we can only dispatch 80% of normal supply.
        # Since supply is NOT limiting in preliminary dataset,
        # we model this as: dispatched boxes = min(demand, 0.8 x capacity)
        if scenario_name == 'S2_Supply_Shock' and location_id == S2_SHOCK_LOCATION:
            supply_mult = S2_YIELD_MULT  # 0.8 — farm can only produce 80%
        else:
            supply_mult = 1.0

        cold_boxes    = group[group['strict_cold_chain'] == 1]['weekly_demand_mean_boxes'].sum() * demand_mult * supply_mult
        ambient_boxes = group[group['strict_cold_chain'] == 0]['weekly_demand_mean_boxes'].sum() * demand_mult * supply_mult

        trucks = assign_vehicles(cold_boxes, ambient_boxes)

        for truck in trucks:
            speed         = VEHICLES[truck]['avg_speed_kmph']
            travel_time_h = (distance_km / speed) * mult['time_mult']
            kpis          = calculate_trip_kpis(truck, distance_km, travel_time_h, max_lead_h)

            route_rows.append({
                'Scenario':        scenario_name,
                'farm_id':         farm,
                'customer_id':     customer,
                'location_id':     location_id,
                'distance_km':     round(distance_km, 2),
                'vehicle_type':    truck,
                'travel_time_h':   round(travel_time_h, 2),
                'max_lead_time_h': max_lead_h,
                **kpis
            })

        # ── Spoilage per order line ──────────────────────────
        for _, row in group.iterrows():
            speed       = (VEHICLES['REEFER_TRK']['avg_speed_kmph']
                           if row['strict_cold_chain'] == 1
                           else VEHICLES['LORRY_AMB']['avg_speed_kmph'])
            travel_h    = (row['real_road_distance_km'] / speed) * mult['time_mult']
            dispatched  = row['weekly_demand_mean_boxes'] * demand_mult * supply_mult
            spoiled     = calculate_spoilage(row, travel_h, dispatched)

            spoilage_rows.append({
                'Scenario':         scenario_name,
                'customer_id':      row['customer_id'],
                'sku_id':           row['sku_id'],
                'location_id':      location_id,
                'dispatched_boxes': round(dispatched, 1),
                'spoiled_boxes':    spoiled,
            })

    # ── Scenario Summary ─────────────────────────────────────
    df_r = pd.DataFrame(route_rows)
    df_s = pd.DataFrame(spoilage_rows)

    total_trucks     = len(df_r)
    on_time_count    = df_r['on_time'].sum()
    total_dispatched = df_s['dispatched_boxes'].sum()
    total_spoiled    = df_s['spoiled_boxes'].sum()

    summary_rows.append({
        'Scenario':        scenario_name,
        'Total Trucks':    total_trucks,
        'Total Fuel (L)':  round(df_r['fuel_used_L'].sum(), 1),
        'Fuel Cost (RM)':  round(df_r['fuel_cost_RM'].sum(), 2),
        'Total Cost (RM)': round(df_r['total_cost_RM'].sum(), 2),
        'On-Time %':       round((on_time_count / total_trucks) * 100, 1),
        'Dispatched Boxes': round(total_dispatched, 0),
        'Spoiled Boxes':   round(total_spoiled, 1),
        'Discard Rate %':  round((total_spoiled / total_dispatched) * 100, 2) if total_dispatched > 0 else 0,
    })

    all_route_rows.extend(route_rows)
    all_spoilage_rows.extend(spoilage_rows)

# ============================================================
# PRINT & EXPORT RESULTS
# ============================================================
df_summary  = pd.DataFrame(summary_rows)
df_routes   = pd.DataFrame(all_route_rows)
df_spoilage = pd.DataFrame(all_spoilage_rows)

print("\n" + "=" * 70)
print("      PROPOSAL A — SCENARIO RESULTS (using actual dataset values)")
print("=" * 70)
print(df_summary.to_string(index=False))
print("=" * 70)
print(f"\nNote: S2 supply shock applied to location: {S2_SHOCK_LOCATION}")

with pd.ExcelWriter('Proposal_A_Scenario_Results.xlsx') as writer:
    df_summary.to_excel(writer,  sheet_name='Summary',          index=False)
    df_routes.to_excel(writer,   sheet_name='Route_Detail',     index=False)
    df_spoilage.to_excel(writer, sheet_name='Spoilage_Detail',  index=False)

print("\nExported to 'Proposal_A_Scenario_Results.xlsx'")
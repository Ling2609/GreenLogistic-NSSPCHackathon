import pandas as pd
import math

# ---------------------------------------------------------
# STEP 1: LOAD DATA & DEFINE PARAMETERS
# ---------------------------------------------------------
print("1. Loading Phase A Fulfillment Plan...")
df = pd.read_excel('Phase_A_Fulfillment_Plan.xlsx')
print(f"   Loaded {len(df)} rows.")

VEHICLES = {
    'REEFER_TRK': {'cap': 400, 'cold': 1, 'fixed_cost': 450, 'fuel_l_per_km': 0.38, 'maintenance_rm_per_km': 0.36, 'avg_speed_kmph': 48},
    'LORRY_AMB':  {'cap': 500, 'cold': 0, 'fixed_cost': 280, 'fuel_l_per_km': 0.32, 'maintenance_rm_per_km': 0.30, 'avg_speed_kmph': 50},
    'VAN_AMB':    {'cap': 120, 'cold': 0, 'fixed_cost': 120, 'fuel_l_per_km': 0.12, 'maintenance_rm_per_km': 0.22, 'avg_speed_kmph': 55},
}
FUEL_PRICE = 2.05  # RM per litre

# --- THE SCENARIO MULTIPLIERS ---
SCENARIOS = {
    'S0_Normal':   {'demand': 1.0, 'time': 1.0, 'spoil': 1.0},
    'S1_Flood':    {'demand': 1.0, 'time': 1.5, 'spoil': 1.0}, # Roads flooded -> 1.5x travel time
    'S2_Heatwave': {'demand': 1.2, 'time': 1.0, 'spoil': 1.5}  # Panic buying -> 1.2x demand, Heat -> 1.5x spoilage rate
}

all_routes = []
all_spoilage = []
summary_results = []

# ---------------------------------------------------------
# STEP 2 & 3: THE SCENARIO LOOP
# ---------------------------------------------------------
print("\n2. Running Simulations for S0, S1, and S2...")

for scenario_name, mult in SCENARIOS.items():
    print(f"   -> Simulating {scenario_name}...")
    
    scenario_routes = []
    
    # 2. Assign Vehicles per Route
    for (farm, customer), group in df.groupby(['farm_id', 'customer_id']):
        distance = group['real_road_distance_km'].iloc[0]
        max_lead = group['max_lead_time_h'].iloc[0]

        # APPLY DEMAND MULTIPLIER
        cold_boxes    = group[group['strict_cold_chain'] == 1]['weekly_demand_mean_boxes'].sum() * mult['demand']
        ambient_boxes = group[group['strict_cold_chain'] == 0]['weekly_demand_mean_boxes'].sum() * mult['demand']

        trucks = []

        # Handle cold boxes
        if cold_boxes > 0:
            num_reefers = math.ceil(cold_boxes / VEHICLES['REEFER_TRK']['cap'])
            trucks.extend(['REEFER_TRK'] * num_reefers)
            spare = (num_reefers * VEHICLES['REEFER_TRK']['cap']) - cold_boxes
            overflow = min(spare, ambient_boxes)
            ambient_boxes -= overflow

        # Handle ambient boxes
        remaining = ambient_boxes
        while remaining > 0:
            if remaining > VEHICLES['VAN_AMB']['cap']:
                trucks.append('LORRY_AMB')
                remaining -= VEHICLES['LORRY_AMB']['cap']
            else:
                trucks.append('VAN_AMB')
                remaining -= VEHICLES['VAN_AMB']['cap']

        # Calculate Costs and Time
        for truck in trucks:
            v = VEHICLES[truck]
            # APPLY TRAVEL TIME MULTIPLIER
            travel_time_h  = (distance / v['avg_speed_kmph']) * mult['time']
            
            fuel_l         = distance * v['fuel_l_per_km']
            fuel_cost_rm   = fuel_l * FUEL_PRICE
            maint_cost_rm  = distance * v['maintenance_rm_per_km']
            total_cost_rm  = v['fixed_cost'] + fuel_cost_rm + maint_cost_rm
            on_time        = 1 if travel_time_h <= max_lead else 0

            scenario_routes.append({
                'Scenario':         scenario_name,
                'farm_id':          farm,
                'customer_id':      customer,
                'distance_km':      round(distance, 2),
                'vehicle_type':     truck,
                'travel_time_h':    round(travel_time_h, 2),
                'max_lead_time_h':  max_lead,
                'on_time':          on_time,
                'total_cost_RM':    round(total_cost_rm, 2),
            })
            
    df_routes = pd.DataFrame(scenario_routes)
    all_routes.append(df_routes)

    # 3. Calculate Spoilage
    scenario_spoilage = []
    for _, row in df.iterrows():
        distance   = row['real_road_distance_km']
        speed      = VEHICLES['REEFER_TRK']['avg_speed_kmph'] if row['strict_cold_chain'] == 1 else VEHICLES['LORRY_AMB']['avg_speed_kmph']
        
        # APPLY TIME MULTIPLIER TO TRAVEL, DEMAND TO BOXES, AND SPOILAGE TO RATE
        travel_h   = (distance / speed) * mult['time']
        shelf_life = row['shelf_life_cold_h'] if row['strict_cold_chain'] == 1 else row['shelf_life_ambient_h']
        boxes      = row['weekly_demand_mean_boxes'] * mult['demand']
        spoil_rate = row['spoilage_rate_per_h_after_limit'] * mult['spoil']

        overtime_h     = max(0, travel_h - shelf_life)
        spoiled_boxes  = min(boxes, boxes * spoil_rate * overtime_h)

        scenario_spoilage.append({
            'Scenario':         scenario_name,
            'customer_id':      row['customer_id'],
            'sku_id':           row['sku_id'],
            'dispatched_boxes': boxes,
            'spoiled_boxes':    round(spoiled_boxes, 2),
        })

    df_spoilage = pd.DataFrame(scenario_spoilage)
    all_spoilage.append(df_spoilage)
    
    # 4. Scenario Summary Math
    total_deliveries = len(df_routes)
    on_time_count    = df_routes['on_time'].sum()
    total_dispatched = df_spoilage['dispatched_boxes'].sum()
    total_spoiled    = df_spoilage['spoiled_boxes'].sum()

    summary_results.append({
        'Scenario':               scenario_name,
        'Total Routes / Trucks':  total_deliveries,
        'Total Cost (RM)':        round(df_routes['total_cost_RM'].sum(), 2),
        'On-Time %':              round((on_time_count / total_deliveries) * 100, 1) if total_deliveries > 0 else 0,
        'Discard Rate %':         round((total_spoiled / total_dispatched) * 100, 2) if total_dispatched > 0 else 0,
        'Total Spoiled Boxes':    round(total_spoiled, 1)
    })

# ---------------------------------------------------------
# STEP 4: EXPORT EVERYTHING
# ---------------------------------------------------------
print("\n3. Compiling and Exporting Master Report...")

df_master_summary = pd.DataFrame(summary_results)
df_all_routes = pd.concat(all_routes, ignore_index=True)
df_all_spoilage = pd.concat(all_spoilage, ignore_index=True)

print("\n" + "="*60)
print("             SCENARIO COMPARISON DASHBOARD")
print("="*60)
print(df_master_summary.to_string(index=False))
print("="*60)

with pd.ExcelWriter('Master_Phase_A_KPI_Results.xlsx') as writer:
    # We put the summary on the FIRST sheet so judges see it immediately
    df_master_summary.to_excel(writer, sheet_name='Comparison_Summary', index=False)
    # The detailed data goes on the backup sheets
    df_all_routes.to_excel(writer, sheet_name='All_Routes_Data', index=False)
    df_all_spoilage.to_excel(writer, sheet_name='All_Spoilage_Data', index=False)

print("\nDone! Exported to 'Master_Phase_A_KPI_Results.xlsx'. Open it to see the magic!")
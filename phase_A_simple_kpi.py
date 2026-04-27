import pandas as pd
import math

# ---------------------------------------------------------
# STEP 1: LOAD DATA
# ---------------------------------------------------------
print("1. Loading Phase A Fulfillment Plan...")
df = pd.read_excel('Phase_A_Fulfillment_Plan.xlsx')
print(f"   Loaded {len(df)} rows.")

# ---------------------------------------------------------
# VEHICLE DATA (from your actual dataset)
# ---------------------------------------------------------
VEHICLES = {
    'REEFER_TRK': {'cap': 400, 'cold': 1, 'fixed_cost': 450, 'fuel_l_per_km': 0.38, 'maintenance_rm_per_km': 0.36, 'avg_speed_kmph': 48},
    'LORRY_AMB':  {'cap': 500, 'cold': 0, 'fixed_cost': 280, 'fuel_l_per_km': 0.32, 'maintenance_rm_per_km': 0.30, 'avg_speed_kmph': 50},
    'VAN_AMB':    {'cap': 120, 'cold': 0, 'fixed_cost': 120, 'fuel_l_per_km': 0.12, 'maintenance_rm_per_km': 0.22, 'avg_speed_kmph': 55},
}
FUEL_PRICE = 2.05  # RM per litre

# ---------------------------------------------------------
# STEP 2: ASSIGN VEHICLES PER ROUTE (farm → customer)
# ---------------------------------------------------------
print("2. Assigning vehicles and calculating per-route KPIs...")

route_rows = []

for (farm, customer), group in df.groupby(['farm_id', 'customer_id']):
    distance = group['real_road_distance_km'].iloc[0]
    max_lead = group['max_lead_time_h'].iloc[0]

    cold_boxes    = group[group['strict_cold_chain'] == 1]['weekly_demand_mean_boxes'].sum()
    ambient_boxes = group[group['strict_cold_chain'] == 0]['weekly_demand_mean_boxes'].sum()

    trucks = []

    # Handle cold boxes → must use REEFER_TRK
    if cold_boxes > 0:
        num_reefers = math.ceil(cold_boxes / VEHICLES['REEFER_TRK']['cap'])
        trucks.extend(['REEFER_TRK'] * num_reefers)
        spare = (num_reefers * VEHICLES['REEFER_TRK']['cap']) - cold_boxes
        overflow = min(spare, ambient_boxes)
        ambient_boxes -= overflow  # fill spare reefer space with ambient boxes

    # Handle remaining ambient boxes
    remaining = ambient_boxes
    while remaining > 0:
        if remaining > VEHICLES['VAN_AMB']['cap']:
            trucks.append('LORRY_AMB')
            remaining -= VEHICLES['LORRY_AMB']['cap']
        else:
            trucks.append('VAN_AMB')
            remaining -= VEHICLES['VAN_AMB']['cap']

    # Calculate costs and time for each truck on this route
    for truck in trucks:
        v = VEHICLES[truck]
        travel_time_h  = distance / v['avg_speed_kmph']
        fuel_l         = distance * v['fuel_l_per_km']
        fuel_cost_rm   = fuel_l * FUEL_PRICE
        maint_cost_rm  = distance * v['maintenance_rm_per_km']
        total_cost_rm  = v['fixed_cost'] + fuel_cost_rm + maint_cost_rm
        on_time        = 1 if travel_time_h <= max_lead else 0

        route_rows.append({
            'farm_id':          farm,
            'customer_id':      customer,
            'distance_km':      round(distance, 2),
            'vehicle_type':     truck,
            'travel_time_h':    round(travel_time_h, 2),
            'max_lead_time_h':  max_lead,
            'on_time':          on_time,
            'fuel_used_L':      round(fuel_l, 2),
            'fuel_cost_RM':     round(fuel_cost_rm, 2),
            'fixed_cost_RM':    v['fixed_cost'],
            'maint_cost_RM':    round(maint_cost_rm, 2),
            'total_cost_RM':    round(total_cost_rm, 2),
        })

df_routes = pd.DataFrame(route_rows)

# ---------------------------------------------------------
# STEP 3: CALCULATE DISCARD RATE
# ---------------------------------------------------------
print("3. Calculating spoilage / discard rate...")

spoilage_rows = []
for _, row in df.iterrows():
    distance   = row['real_road_distance_km']
    # Use reefer speed if cold chain required, else ambient van speed
    speed      = VEHICLES['REEFER_TRK']['avg_speed_kmph'] if row['strict_cold_chain'] == 1 else VEHICLES['LORRY_AMB']['avg_speed_kmph']
    travel_h   = distance / speed
    shelf_life = row['shelf_life_cold_h'] if row['strict_cold_chain'] == 1 else row['shelf_life_ambient_h']
    boxes      = row['weekly_demand_mean_boxes']
    spoil_rate = row['spoilage_rate_per_h_after_limit']

    overtime_h     = max(0, travel_h - shelf_life)
    spoiled_boxes  = min(boxes, boxes * spoil_rate * overtime_h)

    spoilage_rows.append({
        'customer_id':    row['customer_id'],
        'sku_id':         row['sku_id'],
        'dispatched_boxes': boxes,
        'spoiled_boxes':  round(spoiled_boxes, 2),
    })

df_spoilage = pd.DataFrame(spoilage_rows)
total_dispatched = df_spoilage['dispatched_boxes'].sum()
total_spoiled    = df_spoilage['spoiled_boxes'].sum()
discard_rate_pct = (total_spoiled / total_dispatched) * 100

# ---------------------------------------------------------
# STEP 4: SUMMARY KPIs
# ---------------------------------------------------------
total_fuel_L      = df_routes['fuel_used_L'].sum()
total_fuel_cost   = df_routes['fuel_cost_RM'].sum()
total_cost        = df_routes['total_cost_RM'].sum()
total_deliveries  = len(df_routes)
on_time_count     = df_routes['on_time'].sum()
on_time_pct       = (on_time_count / total_deliveries) * 100

print("\n" + "="*50)
print("        PROPOSAL A — KPI SUMMARY (S0 Baseline)")
print("="*50)
print(f"  Total Delivery Routes:       {total_deliveries}")
print(f"  Total Vehicles Dispatched:   {df_routes['vehicle_type'].value_counts().to_dict()}")
print(f"  Total Fuel Used (L):         {total_fuel_L:,.1f}")
print(f"  Total Fuel Cost (RM):        RM {total_fuel_cost:,.2f}")
print(f"  Total Cost (RM):             RM {total_cost:,.2f}")
print(f"  On-Time Compliance:          {on_time_pct:.1f}%  ({on_time_count}/{total_deliveries})")
print(f"  Total Dispatched Boxes:      {total_dispatched:,.0f}")
print(f"  Total Spoiled Boxes:         {total_spoiled:.1f}")
print(f"  Discard Rate:                {discard_rate_pct:.2f}%")
print("="*50)

# ---------------------------------------------------------
# STEP 5: EXPORT
# ---------------------------------------------------------
print("\n4. Exporting results...")
with pd.ExcelWriter('Phase_A_KPI_Results.xlsx') as writer:
    df_routes.to_excel(writer, sheet_name='Route_KPIs', index=False)
    df_spoilage.to_excel(writer, sheet_name='Spoilage', index=False)

    summary = pd.DataFrame([{
        'Total Routes':         total_deliveries,
        'Total Fuel L':         round(total_fuel_L, 1),
        'Total Fuel Cost RM':   round(total_fuel_cost, 2),
        'Total Cost RM':        round(total_cost, 2),
        'On-Time %':            round(on_time_pct, 1),
        'Discard Rate %':       round(discard_rate_pct, 2),
        'Total Dispatched Boxes': total_dispatched,
        'Total Spoiled Boxes':  round(total_spoiled, 1),
    }])
    summary.to_excel(writer, sheet_name='Summary', index=False)

print("Done! Exported to Phase_A_KPI_Results.xlsx")
import pandas as pd
import numpy as np

print("1. Loading Pillar 1 and Pillar 2...")
# Note: Ensure the filenames match exactly what is in your folder!
df_supply = pd.read_excel('Pillar1_Master_Supply_Complete.xlsx')
df_demand = pd.read_excel('Pillar2_Master_Demand.xlsx')

print("2. Matching Demand to Supply...")
# We merge them based on the vegetable (sku_id). 
# This explodes the 212 orders into all possible farm combinations.
df_matches = pd.merge(
    df_demand,
    df_supply,
    on='sku_id',
    how='inner'
)

print("3. Calculating Distances...")
def calculate_distance(lat1, lon1, lat2, lon2):
    """Calculates straight-line distance in km using the Haversine formula."""
    R = 6371.0 
    lat1, lon1, lat2, lon2 = map(np.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = np.sin(dlat/2)**2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon/2)**2
    c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1-a))
    return R * c

# Calculate distance for every possible match
df_matches['distance_km'] = calculate_distance(
    df_matches['farm_lat'], df_matches['farm_lon'], 
    df_matches['cust_lat'], df_matches['cust_lon']
)

# Apply our real-world circuity factor!
df_matches['real_road_distance_km'] = df_matches['distance_km'] * 1.3

print("4. Selecting the Best Farm for Each Order...")
# Sort by Customer -> SKU -> Shortest Distance
df_matches = df_matches.sort_values(by=['customer_id', 'sku_id', 'real_road_distance_km'])

# Group by the specific order, and pick the first (closest) farm in the sorted list
df_final_allocation = df_matches.groupby(['customer_id', 'sku_id']).first().reset_index()

# Determine if the order needs a Reefer truck (If customer asks OR if product needs it)
df_final_allocation['strict_cold_chain'] = df_final_allocation[['cold_storage_requested', 'cold_required']].max(axis=1)

print("\n--- PHASE A: ALLOCATION COMPLETE ---")
print(f"Successfully allocated {len(df_final_allocation)} orders to farms.")
print("First 3 Allocations:")
print(df_final_allocation[['customer_id', 'customer_name', 'sku_id', 'farm_id', 'real_road_distance_km']].head(3).to_string())

# Export the final matched list
export_name = "Phase_A_Fulfillment_Plan.xlsx"
df_final_allocation.to_excel(export_name, index=False)
print(f"\nExported Fulfillment Plan to '{export_name}'.")
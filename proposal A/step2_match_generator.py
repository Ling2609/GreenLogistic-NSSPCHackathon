import pandas as pd
import numpy as np

FILE_NAME = 'Dataset_Preliminary_Presentation_v10 (1).xlsx'

print("========================================")
print(" STEP 1 & 2: GENERATING POSSIBLE MATCHES")
print("========================================")

# --- REUSING STEP 1 (DATA LOADER) ---
print("1. Loading and Cleaning Data...")
df_farms         = pd.read_excel(FILE_NAME, sheet_name='Farms')
df_products      = pd.read_excel(FILE_NAME, sheet_name='Products')
df_farm_products = pd.read_excel(FILE_NAME, sheet_name='Farm_Products')
df_demand        = pd.read_excel(FILE_NAME, sheet_name='Demand')
df_customers     = pd.read_excel(FILE_NAME, sheet_name='Customers')

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

# ---------------------------------------------------------
# STEP 2. ASSEMBLE THE MASTER MENUS
# ---------------------------------------------------------
print("2. Building Master Supply and Demand Menus...")

# Master Supply Menu
df_supply = df_farm_products.copy()
df_supply = pd.merge(df_supply, df_farms, on='farm_id', how='left')
df_supply = pd.merge(df_supply, df_products, on='sku_id', how='left')
df_supply.rename(columns={'lat': 'farm_lat', 'lon': 'farm_lon'}, inplace=True)

# Master Demand Menu
df_demand_menu = df_demand.copy()
df_demand_menu = pd.merge(df_demand_menu, df_customers, on='customer_id', how='left')
df_demand_menu.rename(columns={'lat': 'cust_lat', 'lon': 'cust_lon'}, inplace=True)

# ---------------------------------------------------------
# STEP 2b. CREATE ALL POSSIBLE MATCHES
# ---------------------------------------------------------
print("3. Matching Orders to Farms based on Vegetable Type (sku_id)...")
df_matches = pd.merge(df_demand_menu, df_supply, on='sku_id', how='inner')

# ---------------------------------------------------------
# STEP 2c. CALCULATE DISTANCES
# ---------------------------------------------------------
print("4. Calculating real-world driving distances for all matches...")

def get_distance(lat1, lon1, lat2, lon2):
    """Haversine formula * 1.3 circuity"""
    R = 6371.0 
    lat1, lon1, lat2, lon2 = map(np.radians, [lat1, lon1, lat2, lon2])
    a = np.sin((lat2 - lat1)/2)**2 + np.cos(lat1) * np.cos(lat2) * np.sin((lon2 - lon1)/2)**2
    c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1-a))
    return (R * c) * 1.3

df_matches['distance_km'] = get_distance(
    df_matches['farm_lat'], df_matches['farm_lon'], 
    df_matches['cust_lat'], df_matches['cust_lon']
)

# Figure out if the truck needs to be cold!
df_matches['strict_cold_chain'] = df_matches[['cold_storage_requested', 'cold_required']].max(axis=1)

# Sort by Customer -> SKU -> Shortest Distance
df_matches = df_matches.sort_values(by=['customer_id', 'sku_id', 'distance_km'])

# ---------------------------------------------------------
# VERIFY RESULTS
# ---------------------------------------------------------
print("\n--- MATCH GENERATOR COMPLETE ---")
print(f"Total possible routing combinations found: {len(df_matches)}")
print("========================================\n")

# Save this to an Excel file so we can look at it if we need to!
df_matches.to_excel("Step2_All_Possible_Matches.xlsx", index=False)
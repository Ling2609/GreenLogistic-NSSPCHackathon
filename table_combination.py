import pandas as pd
import numpy as np

# ---------------------------------------------------------
# STEP 1: LOAD DATA
# ---------------------------------------------------------
file_path = 'Dataset_Preliminary_Presentation_v10 (1).xlsx'
print("1. Loading raw data from Excel...")

df_demand = pd.read_excel(file_path, sheet_name='Demand')
df_customers = pd.read_excel(file_path, sheet_name='Customers')
df_products = pd.read_excel(file_path, sheet_name='Products')
df_farm_products = pd.read_excel(file_path, sheet_name='Farm_Products')
df_farms = pd.read_excel(file_path, sheet_name='Farms')


# ---------------------------------------------------------
# STEP 2: DATA CLEANING
# ---------------------------------------------------------
print("2. Initiating Data Cleaning...")

def clean_keys(df, columns):
    """Strips invisible spaces and forces uppercase to prevent merge errors."""
    for col in columns:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip().str.upper()
    return df

# Apply cleaning to all Primary and Foreign Keys
df_demand = clean_keys(df_demand, ['customer_id', 'sku_id'])
df_customers = clean_keys(df_customers, ['customer_id'])
df_products = clean_keys(df_products, ['sku_id'])
df_farm_products = clean_keys(df_farm_products, ['sku_id', 'farm_id'])
df_farms = clean_keys(df_farms, ['farm_id'])


# ---------------------------------------------------------
# STEP 3: PHASE 1 - BUILD MASTER ORDERS
# ---------------------------------------------------------
print("3. Building the Master Order Table...")
df_master = df_demand.copy()

# JOIN Customers (Where is it going, and what are the time limits?)
df_master = pd.merge(
    df_master, 
    df_customers[['customer_id', 'lat', 'lon', 'state', 'delivery_window', 'max_lead_time_h','cold_storage_requested']], 
    on='customer_id', 
    how='left'
)
df_master.rename(columns={'lat': 'cust_lat', 'lon': 'cust_lon'}, inplace=True)

# JOIN Products (Does it need a Reefer Truck?)
df_master = pd.merge(
    df_master,
    df_products[['sku_id', 'cold_required']], 
    on='sku_id',
    how='left'
)

# Create the ultimate cold chain rule: If either the customer OR the product needs it, make it 1.
df_master['strict_cold_chain'] = df_master[['cold_storage_requested', 'cold_required']].max(axis=1)

# ---------------------------------------------------------
# STEP 4: PHASE 2 - THE FARM MATCHER
# ---------------------------------------------------------
print("4. Exploding options via The Farm Matcher...")

# JOIN Farm Products (Who grows this vegetable?)
# Inner join creates multiple rows per order if multiple farms grow the SKU
df_options = pd.merge(
    df_master,
    df_farm_products[['sku_id', 'farm_id', 'daily_capacity_boxes', 'unit_cost_rm_per_box', 'available_days']],
    on='sku_id',
    how='inner' 
)

df_options.rename(columns={'available_days': 'farm_products_available_days'}, inplace=True)

# JOIN Farms (Where are these farms located?)
df_options = pd.merge(
    df_options,
    df_farms[['farm_id', 'farm_name', 'lat', 'lon', 'harvest_days']],
    on='farm_id',
    how='left'
)
df_options.rename(columns={'lat': 'farm_lat', 'lon': 'farm_lon'}, inplace=True)


# ---------------------------------------------------------
# STEP 5: CALCULATE DISTANCES
# ---------------------------------------------------------
print("5. Calculating exact route distances...")

def calculate_distance(lat1, lon1, lat2, lon2):
    """Calculates straight-line distance in km using the Haversine formula."""
    R = 6371.0 # Earth radius in kilometers
    
    lat1, lon1, lat2, lon2 = map(np.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    
    a = np.sin(dlat/2)**2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon/2)**2
    c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1-a))
    
    return R * c

# Apply the math to every single potential route combination
df_options['distance_km'] = calculate_distance(
    df_options['farm_lat'], df_options['farm_lon'], 
    df_options['cust_lat'], df_options['cust_lon']
)


# ---------------------------------------------------------
# STEP 6: SORT AND EXPORT
# ---------------------------------------------------------
# Sort by Customer -> Product -> Closest Distance
df_options = df_options.sort_values(by=['customer_id', 'sku_id', 'distance_km'])

print("\n========================================")
print("         PIPELINE COMPLETE              ")
print("========================================")
print(f"Total original orders: {len(df_master)}")
print(f"Total potential routes generated: {len(df_options)}")
print("========================================\n")

# export_filename = "Master_Route_Options.csv"
# df_options.to_csv(export_filename, index=False)
# print(f"Success! Data exported to '{export_filename}'.")

export_filename = "Master_Route_Options.xlsx"
df_options.to_excel(export_filename, index=False)
print(f"Success! Data exported to '{export_filename}'.")
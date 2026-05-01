import pandas as pd

# The exact filename of your dataset
FILE_NAME = 'Dataset_Preliminary_Presentation_v10 (1).xlsx'

print("========================================")
print(" STEP 1: LOADING AND CLEANING DATA")
print("========================================")

# ---------------------------------------------------------
# 1. LOAD THE SHEETS
# ---------------------------------------------------------
print(f"Reading {FILE_NAME}...")
df_farms         = pd.read_excel(FILE_NAME, sheet_name='Farms')
df_products      = pd.read_excel(FILE_NAME, sheet_name='Products')
df_farm_products = pd.read_excel(FILE_NAME, sheet_name='Farm_Products')

df_demand        = pd.read_excel(FILE_NAME, sheet_name='Demand')
df_customers     = pd.read_excel(FILE_NAME, sheet_name='Customers')

# ---------------------------------------------------------
# 2. DEFINE THE MASTER CLEANING FUNCTION
# ---------------------------------------------------------
def clean_ids(df, id_columns):
    """
    Forces all ID columns to be text, removes invisible spaces, 
    and makes them uppercase so merging is 100% reliable.
    """
    for col in id_columns:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip().str.upper()
    return df

# ---------------------------------------------------------
# 3. APPLY CLEANING TO ALL CRITICAL TABLES
# ---------------------------------------------------------
print("Scrubbing ID columns for invisible spaces...")

# Clean Supply Side IDs
df_farms         = clean_ids(df_farms, ['farm_id', 'location_id'])
df_products      = clean_ids(df_products, ['sku_id'])
df_farm_products = clean_ids(df_farm_products, ['farm_id', 'sku_id'])

# Clean Demand Side IDs
df_demand        = clean_ids(df_demand, ['customer_id', 'sku_id'])
df_customers     = clean_ids(df_customers, ['customer_id'])

# ---------------------------------------------------------
# 4. VERIFY THE RESULTS
# ---------------------------------------------------------
print("\n--- DATA SUCCESSFULLY LOADED ---")
print(f"Farms:           {len(df_farms)} rows")
print(f"Products:        {len(df_products)} rows")
print(f"Farm Inventory:  {len(df_farm_products)} rows")
print(f"Customers:       {len(df_customers)} rows")
print(f"Demand Orders:   {len(df_demand)} rows")
print("========================================\n")
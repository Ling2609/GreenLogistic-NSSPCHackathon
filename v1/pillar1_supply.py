import pandas as pd

# ---------------------------------------------------------
# 1. LOAD ONLY PILLAR 1 DATA
# ---------------------------------------------------------
file_path = 'Dataset_Preliminary_Presentation_v10 (1).xlsx'
print("Loading Pillar 1 Data (Supply)...")

df_farms = pd.read_excel(file_path, sheet_name='Farms')
df_products = pd.read_excel(file_path, sheet_name='Products')
df_farm_products = pd.read_excel(file_path, sheet_name='Farm_Products')

def clean_keys(df, columns):
    for col in columns:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip().str.upper()
    return df

df_farms = clean_keys(df_farms, ['farm_id'])
df_products = clean_keys(df_products, ['sku_id'])
df_farm_products = clean_keys(df_farm_products, ['sku_id', 'farm_id'])

# ---------------------------------------------------------
# 2. ASSEMBLE THE MASTER SUPPLY MENU (ALL COLUMNS)
# ---------------------------------------------------------
print("Assembling the Master Supply Menu...")

# Start with the bridge table
df_supply = df_farm_products.copy()

# Add EVERYTHING from Farms
df_supply = pd.merge(
    df_supply,
    df_farms, # Notice we are passing the whole table now
    on='farm_id',
    how='left'
)
df_supply.rename(columns={'lat': 'farm_lat', 'lon': 'farm_lon'}, inplace=True)

# Add EVERYTHING from Products
df_supply = pd.merge(
    df_supply,
    df_products, # Passing the whole table here too
    on='sku_id',
    how='left'
)

print("\n--- PILLAR 1: SUPPLY MENU ---")
print(f"Total Columns Kept: {len(df_supply.columns)}")
print("Columns included:", df_supply.columns.tolist())

# Export as .xlsx
export_name = "Pillar1_Master_Supply.xlsx"
df_supply.to_excel(export_name, index=False)
print(f"\nExported complete inventory to '{export_name}'.")
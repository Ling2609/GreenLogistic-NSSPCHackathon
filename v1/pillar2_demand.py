import pandas as pd

# ---------------------------------------------------------
# 1. LOAD ONLY PILLAR 2 DATA
# ---------------------------------------------------------
file_path = 'Dataset_Preliminary_Presentation_v10 (1).xlsx'
print("Loading Pillar 2 Data (Demand)...")

df_demand = pd.read_excel(file_path, sheet_name='Demand')
df_customers = pd.read_excel(file_path, sheet_name='Customers')

# Clean the IDs to ensure perfect merging, just like we did for Supply
def clean_keys(df, columns):
    for col in columns:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip().str.upper()
    return df

df_demand = clean_keys(df_demand, ['customer_id', 'sku_id'])
df_customers = clean_keys(df_customers, ['customer_id'])

# ---------------------------------------------------------
# 2. ASSEMBLE THE MASTER DEMAND MENU
# ---------------------------------------------------------
print("Assembling the Master Demand Menu...")

# Start with the core shopping list
df_demand_menu = df_demand.copy()

# Add EVERYTHING from the Customers table (Where are they, and what are their rules?)
df_demand_menu = pd.merge(
    df_demand_menu,
    df_customers,
    on='customer_id',
    how='left'
)

# Rename coordinates so we don't confuse them with farm coordinates later
df_demand_menu.rename(columns={'lat': 'cust_lat', 'lon': 'cust_lon'}, inplace=True)

# ---------------------------------------------------------
# 3. VERIFY AND EXPORT
# ---------------------------------------------------------
print("\n--- PILLAR 2: DEMAND MENU ---")
print(f"Total Unique Orders to Fulfill: {len(df_demand_menu)}")
print("Here are the first 3 orders:")
# Just printing a few key columns to the terminal so it's readable
print(df_demand_menu[['customer_id', 'customer_name', 'sku_id', 'weekly_demand_mean_boxes', 'delivery_window']].head(3).to_string())

# Export to Excel
export_name = "Pillar2_Master_Demand.xlsx"
df_demand_menu.to_excel(export_name, index=False)
print(f"\nExported clean shopping list to '{export_name}'.")
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
import os

app = FastAPI(title="GreenLogistics AI API")

# Allow React to talk to Python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- THE DATA ENGINE ---
# Find the exact folder this script is in
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FILE_PATH = os.path.join(BASE_DIR, "Dataset_Preliminary_Presentation_v10 (1).xlsx")

print("Booting up AI Data Engine...")
try:
    # 1. Read the Excel sheets
    df_demand = pd.read_excel(FILE_PATH, sheet_name='Demand')
    df_customers = pd.read_excel(FILE_PATH, sheet_name='Customers')
    
    # 2. Clean the IDs so they match perfectly
    df_demand['customer_id'] = df_demand['customer_id'].astype(str).str.strip().str.upper()
    df_customers['customer_id'] = df_customers['customer_id'].astype(str).str.strip().str.upper()
    
    # 3. Merge them! Now every order has a Latitude and Longitude
    df_live_orders = pd.merge(df_demand, df_customers, on='customer_id', how='inner')
    
    # 4. Rename the columns to match what our React Frontend expects
    df_live_orders = df_live_orders.rename(columns={
        'sku_id': 'sku',
        'weekly_demand_mean_boxes': 'boxes',
        'state': 'region'
    })
    
    # Generate a fake order ID for the map to use
    df_live_orders['order_id'] = range(1, len(df_live_orders) + 1)
    
    # 5. Convert the DataFrame into a normal Python Dictionary
    REAL_DATABASE = df_live_orders.to_dict(orient="records")
    print(f"✅ Successfully loaded {len(REAL_DATABASE)} real orders from the dataset!")

except Exception as e:
    print(f"❌ ERROR LOADING EXCEL: {e}")
    REAL_DATABASE = []

# --- API ENDPOINTS ---
@app.get("/")
def read_root():
    return {"message": "Welcome to the GreenLogistics API. The AI brain is online."}

@app.get("/api/orders/pending")
def get_pending_orders():
    # Instead of the fake cabbage data, we send the REAL database!
    return REAL_DATABASE
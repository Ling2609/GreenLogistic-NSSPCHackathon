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
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FILE_PATH = os.path.join(BASE_DIR, "Dataset_Preliminary_Presentation_v10 (1).xlsx")

print("Booting up AI Data Engine...")
try:
    df_demand = pd.read_excel(FILE_PATH, sheet_name='Demand')
    df_customers = pd.read_excel(FILE_PATH, sheet_name='Customers')
    
    df_demand['customer_id'] = df_demand['customer_id'].astype(str).str.strip().str.upper()
    df_customers['customer_id'] = df_customers['customer_id'].astype(str).str.strip().str.upper()
    
    df_live_orders = pd.merge(df_demand, df_customers, on='customer_id', how='inner')
    
    # NEW: Group the data! 
    # Instead of 1,000 rows, we collapse it down to 1 row per customer
    df_grouped = df_live_orders.groupby(['customer_id', 'lat', 'lon', 'state']).agg(
        total_boxes=('weekly_demand_mean_boxes', 'sum'),
        # Create a clean list of what they ordered (e.g., "SKU_CUC, SKU_TOM")
        items_ordered=('sku_id', lambda x: ', '.join(x.unique()))
    ).reset_index()
    
    # Convert to dictionary for React
    REAL_DATABASE = df_grouped.to_dict(orient="records")
    print(f"✅ Successfully aggregated down to {len(REAL_DATABASE)} unique Supermarket deliveries!")

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
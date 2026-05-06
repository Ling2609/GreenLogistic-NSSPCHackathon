from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
import os
import math

app = FastAPI(title="GreenLogistics AI API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- THE DATA & AI ENGINE ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FILE_PATH = os.path.join(BASE_DIR, "Dataset_Preliminary_Presentation_v10 (1).xlsx")

print("Booting up AI Routing Engine...")
try:
    df_demand = pd.read_excel(FILE_PATH, sheet_name='Demand')
    df_customers = pd.read_excel(FILE_PATH, sheet_name='Customers')
    df_farms = pd.read_excel(FILE_PATH, sheet_name='Farms') # NEW: Load Farms!
    
    df_demand['customer_id'] = df_demand['customer_id'].astype(str).str.strip().str.upper()
    df_customers['customer_id'] = df_customers['customer_id'].astype(str).str.strip().str.upper()
    
    # 1. Prepare Customers
    df_live_orders = pd.merge(df_demand, df_customers, on='customer_id', how='inner')
    df_grouped = df_live_orders.groupby(['customer_id', 'lat', 'lon', 'state']).agg(
        total_boxes=('weekly_demand_mean_boxes', 'sum')
    ).reset_index()
    REAL_DATABASE = df_grouped.to_dict(orient="records")

    # 2. Prepare the Farm (Let's use the first farm, e.g., Cameron Highlands)
    farm_lat = df_farms.iloc[0]['lat']
    farm_lon = df_farms.iloc[0]['lon']
    farm_name = df_farms.iloc[0]['farm_id']

    # 3. THE AI TSP ALGORITHM (Nearest Neighbor)
    def calculate_milk_runs():
        # Group customers by state so we have regional milk runs
        routes = []
        for state, group in df_grouped.groupby('state'):
            unvisited = group.to_dict('records')
            
            # Start at the farm
            curr_lat, curr_lon = farm_lat, farm_lon
            route_coords = [[farm_lat, farm_lon]]
            
            while unvisited:
                best_dist = float('inf')
                best_idx = 0
                # Find the closest next supermarket
                for i, c in enumerate(unvisited):
                    # Simple distance calculation proxy
                    d = math.hypot(curr_lat - c['lat'], curr_lon - c['lon'])
                    if d < best_dist:
                        best_dist = d
                        best_idx = i
                
                # Move truck to the closest supermarket
                next_stop = unvisited.pop(best_idx)
                route_coords.append([next_stop['lat'], next_stop['lon']])
                curr_lat, curr_lon = next_stop['lat'], next_stop['lon']
                
            # Drive empty truck back to the farm (Reverse Logistics!)
            route_coords.append([farm_lat, farm_lon])
            
            routes.append({
                "region": state,
                "path": route_coords
            })
        return routes

    AI_ROUTES = calculate_milk_runs()
    print("✅ AI TSP Algorithm successfully calculated all Milk Runs!")

except Exception as e:
    print(f"❌ ERROR LOADING EXCEL: {e}")
    REAL_DATABASE = []
    AI_ROUTES = []
    farm_lat, farm_lon, farm_name = 0, 0, ""

# --- API ENDPOINTS ---
@app.get("/api/orders/pending")
def get_pending_orders():
    return REAL_DATABASE

# NEW ENDPOINT: Send the drawn lines and farm data to React!
@app.get("/api/routes/optimized")
def get_optimized_routes():
    return {
        "farm": {"name": farm_name, "lat": farm_lat, "lon": farm_lon},
        "milk_runs": AI_ROUTES
    }
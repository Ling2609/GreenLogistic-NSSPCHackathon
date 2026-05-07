from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
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

# --- THE DATA MODELS ---
# This tells Python exactly what a "New Order" from React should look like
class NewOrder(BaseModel):
    customer_id: str
    state: str
    total_boxes: int
    lat: float
    lon: float

# Global variables to hold our live state
REAL_DATABASE = []
AI_ROUTES = []
farm_lat, farm_lon, farm_name = 0, 0, ""

# --- THE AI ENGINE ---
def calculate_milk_runs(database):
    """Calculates the nearest neighbor TSP routes based on the current live database"""
    routes = []
    
    # Group the database by state manually
    states = set([row['state'] for row in database])
    
    for state in states:
        unvisited = [row for row in database if row['state'] == state]
        route_total_boxes = sum([row['total_boxes'] for row in unvisited])
        
        curr_lat, curr_lon = farm_lat, farm_lon
        route_coords = [[farm_lat, farm_lon]]
        
        while unvisited:
            best_dist = float('inf')
            best_idx = 0
            for i, c in enumerate(unvisited):
                d = math.hypot(curr_lat - c['lat'], curr_lon - c['lon'])
                if d < best_dist:
                    best_dist = d
                    best_idx = i
            
            next_stop = unvisited.pop(best_idx)
            route_coords.append([next_stop['lat'], next_stop['lon']])
            curr_lat, curr_lon = next_stop['lat'], next_stop['lon']
            
        route_coords.append([farm_lat, farm_lon])
        
        routes.append({
            "region": state,
            "path": route_coords,
            "total_load": int(route_total_boxes),
            "stops": len([row for row in database if row['state'] == state])
        })
    return routes

# --- INITIAL BOOT SEQUENCE ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FILE_PATH = os.path.join(BASE_DIR, "Dataset_Preliminary_Presentation_v10 (1).xlsx")

print("Booting up AI Routing Engine...")
try:
    df_demand = pd.read_excel(FILE_PATH, sheet_name='Demand')
    df_customers = pd.read_excel(FILE_PATH, sheet_name='Customers')
    df_farms = pd.read_excel(FILE_PATH, sheet_name='Farms')
    
    df_demand['customer_id'] = df_demand['customer_id'].astype(str).str.strip().str.upper()
    df_customers['customer_id'] = df_customers['customer_id'].astype(str).str.strip().str.upper()
    
    df_live_orders = pd.merge(df_demand, df_customers, on='customer_id', how='inner')
    df_grouped = df_live_orders.groupby(['customer_id', 'lat', 'lon', 'state']).agg(
        total_boxes=('weekly_demand_mean_boxes', 'sum'),
        items_ordered=('sku_id', lambda x: ', '.join(x.unique()))
    ).reset_index()
    REAL_DATABASE = df_grouped.to_dict(orient="records")

    farm_lat = df_farms.iloc[0]['lat']
    farm_lon = df_farms.iloc[0]['lon']
    farm_name = df_farms.iloc[0]['farm_id']

    # Generate initial routes
    AI_ROUTES = calculate_milk_runs(REAL_DATABASE)
    print("✅ System Online!")

except Exception as e:
    print(f"❌ ERROR: {e}")


# --- API ENDPOINTS ---
@app.get("/api/orders/pending")
def get_pending_orders():
    return REAL_DATABASE

@app.get("/api/routes/optimized")
def get_optimized_routes():
    return {
        "farm": {"name": farm_name, "lat": farm_lat, "lon": farm_lon},
        "milk_runs": AI_ROUTES
    }

# NEW: The endpoint to receive data from React!
@app.post("/api/orders/new")
def create_new_order(order: NewOrder):
    global REAL_DATABASE, AI_ROUTES
    
    # 1. Add the new order to our live Python database
    new_entry = {
        "customer_id": order.customer_id,
        "state": order.state,
        "lat": order.lat,
        "lon": order.lon,
        "total_boxes": order.total_boxes,
        "items_ordered": "MANUAL_ENTRY_AD_HOC"
    }
    REAL_DATABASE.append(new_entry)
    
    # 2. Recalculate the AI Routes instantly!
    AI_ROUTES = calculate_milk_runs(REAL_DATABASE)
    
    return {"message": "Order added and routes recalculated!", "total_orders": len(REAL_DATABASE)}
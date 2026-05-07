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

class SimulationSettings(BaseModel):
    new_capacity: int
    
class NewOrder(BaseModel):
    customer_id: str
    state: str
    total_boxes: int
    lat: float
    lon: float

REAL_DATABASE = []
AI_ROUTES = []
farm_lat, farm_lon, farm_name = 0, 0, ""

# --- THE CVRP AI ENGINE (UPGRADED) ---
REAL_DATABASE = []
AI_ROUTES = []
farm_lat, farm_lon, farm_name = 0, 0, ""
TRUCK_CAPACITY = 800 # Now a dynamic global variable!

def calculate_milk_runs(database):
    """Calculates Capacitated Vehicle Routing Problem (CVRP)"""
    routes = []
    states = set([row['state'] for row in database])
    
    for state in states:
        unvisited = [row for row in database if row['state'] == state]
        truck_number = 1
        
        while unvisited:
            # Spawn a new truck at the farm
            curr_lat, curr_lon = farm_lat, farm_lon
            route_coords = [[farm_lat, farm_lon]]
            current_load = 0
            route_stops = 0
            
            while unvisited:
                best_dist = float('inf')
                best_idx = -1
                
                # Look for the closest customer that STILL FITS in the truck
                for i, c in enumerate(unvisited):
                    if current_load + c['total_boxes'] <= TRUCK_CAPACITY:
                        d = math.hypot(curr_lat - c['lat'], curr_lon - c['lon'])
                        if d < best_dist:
                            best_dist = d
                            best_idx = i
                
                # If no one else fits, send the truck back to the farm!
                if best_idx == -1:
                    # Edge case: What if a single customer ordered 1000 boxes? (More than max capacity)
                    # We assign them a dedicated oversized truck.
                    if current_load == 0:
                        best_idx = 0
                    else:
                        break
                
                # Drive truck to the customer and load the boxes
                next_stop = unvisited.pop(best_idx)
                route_coords.append([next_stop['lat'], next_stop['lon']])
                curr_lat, curr_lon = next_stop['lat'], next_stop['lon']
                current_load += next_stop['total_boxes']
                route_stops += 1
                
            # Drive empty truck back to the farm
            route_coords.append([farm_lat, farm_lon])
            
            routes.append({
                "region": f"{state} (Truck {truck_number})",
                "path": route_coords,
                "total_load": int(current_load),
                "stops": route_stops
            })
            truck_number += 1
            
    return routes

# --- INITIAL BOOT SEQUENCE ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FILE_PATH = os.path.join(BASE_DIR, "Dataset_Preliminary_Presentation_v10 (1).xlsx")

print("Booting up Advanced CVRP Routing Engine...")
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

    AI_ROUTES = calculate_milk_runs(REAL_DATABASE)
    print("✅ System Online! Capacitated limits applied.")

except Exception as e:
    print(f"❌ ERROR: {e}")

@app.get("/api/orders/pending")
def get_pending_orders():
    return REAL_DATABASE

@app.get("/api/routes/optimized")
def get_optimized_routes():
    return {
        "farm": {"name": farm_name, "lat": farm_lat, "lon": farm_lon},
        "milk_runs": AI_ROUTES
    }

@app.post("/api/orders/new")
def create_new_order(order: NewOrder):
    global REAL_DATABASE, AI_ROUTES
    
    new_entry = {
        "customer_id": order.customer_id,
        "state": order.state,
        "lat": order.lat,
        "lon": order.lon,
        "total_boxes": order.total_boxes,
        "items_ordered": "MANUAL_ENTRY_AD_HOC"
    }
    REAL_DATABASE.append(new_entry)
    
    # AI instantly recalculates CVRP limits with the new data!
    AI_ROUTES = calculate_milk_runs(REAL_DATABASE)
    
    return {"message": "Order added and routes recalculated!", "total_orders": len(REAL_DATABASE)}

@app.post("/api/settings/capacity")
def update_truck_capacity(settings: SimulationSettings):
    global TRUCK_CAPACITY, AI_ROUTES, REAL_DATABASE
    
    # Update the global rule
    TRUCK_CAPACITY = settings.new_capacity
    
    # Instantly force the AI to recalculate every route in Malaysia based on the new rule!
    AI_ROUTES = calculate_milk_runs(REAL_DATABASE)
    
    return {
        "message": f"Capacity updated to {TRUCK_CAPACITY} boxes. Routes recalculated.", 
        "total_trucks": len(AI_ROUTES)
    }
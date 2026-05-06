from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="GreenLogistics AI API")

# This tells Python to allow our React app to talk to it!
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"message": "Welcome to the GreenLogistics API. The AI brain is online."}

@app.get("/api/orders/pending")
def get_pending_orders():
    return [
        {"order_id": 1, "customer_id": 101, "sku": "Cabbage", "boxes": 400, "region": "Selangor", "lat": 3.0738, "lon": 101.5183},
        {"order_id": 2, "customer_id": 102, "sku": "Frozen Corn", "boxes": 200, "region": "Selangor", "lat": 3.1149, "lon": 101.6288}
    ]
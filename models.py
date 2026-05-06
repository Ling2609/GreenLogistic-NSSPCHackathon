from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey
from sqlalchemy.orm import declarative_base

# This tells SQLAlchemy how to map our Python code to the SQL database
Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    
    user_id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    password_hash = Column(String)
    role = Column(String) # 'FARM', 'SUPERMARKET', 'ADMIN'

class Location(Base):
    __tablename__ = "locations"
    
    location_id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.user_id"))
    address_text = Column(String)
    latitude = Column(Float)
    longitude = Column(Float)
    state_region = Column(String)

class Order(Base):
    __tablename__ = "orders"
    
    order_id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("users.user_id"))
    sku_name = Column(String) # e.g., "Cabbage"
    quantity_boxes = Column(Integer)
    requires_cold = Column(Boolean, default=False)
    status = Column(String, default="PENDING") # PENDING, DISPATCHED
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Float
from sqlalchemy.orm import Session
from database import Base

class Resource(Base):
    __tablename__ = "resources"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False, unique=True)
    category = Column(String, nullable=False)  # "personnel" | "vehicle" | "equipment"
    total_count = Column(Integer, nullable=False)
    available_count = Column(Integer, nullable=False)
    unit = Column(String, nullable=False)  # "persons", "units", "vehicles"
    description = Column(String, nullable=True)

class Allocation(Base):
    __tablename__ = "allocations"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    incident_id = Column(String, nullable=False)
    incident_address = Column(String, nullable=False)
    resource_id = Column(Integer, ForeignKey("resources.id"), nullable=False)
    quantity_allocated = Column(Integer, nullable=False)
    allocated_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    released_at = Column(DateTime, nullable=True)  # Null means still deployed
    status = Column(String, nullable=False)  # "active" | "released"
    notes = Column(String, nullable=True)

def seed_resources(db: Session):
    """
    Inserts default Bengaluru Traffic Police resources if the table is empty.
    """
    if db.query(Resource).first() is not None:
        return
        
    defaults = [
        # Personnel
        Resource(
            name="Traffic Officer", category="personnel", total_count=150, available_count=150, 
            unit="persons", description="Standard traffic patrol officer"
        ),
        Resource(
            name="Traffic Inspector", category="personnel", total_count=20, available_count=20, 
            unit="persons", description="Senior traffic operations supervisor"
        ),
        Resource(
            name="Home Guard", category="personnel", total_count=80, available_count=80, 
            unit="persons", description="Auxiliary support staff"
        ),
        
        # Vehicles
        Resource(
            name="Patrol Car", category="vehicle", total_count=30, available_count=30, 
            unit="vehicles", description="Standard police interceptor/patrol vehicle"
        ),
        Resource(
            name="Ambulance", category="vehicle", total_count=10, available_count=10, 
            unit="vehicles", description="Emergency medical response vehicle"
        ),
        Resource(
            name="Tow Truck", category="vehicle", total_count=15, available_count=15, 
            unit="vehicles", description="Vehicle clearing tow truck"
        ),
        Resource(
            name="Water Tanker", category="vehicle", total_count=8, available_count=8, 
            unit="vehicles", description="Water tanker for waterlogging/fire suppression"
        ),
        
        # Equipment
        Resource(
            name="Heavy Crane", category="equipment", total_count=5, available_count=5, 
            unit="units", description="Heavy lift crane for large vehicle removal"
        ),
        Resource(
            name="Chainsaw", category="equipment", total_count=12, available_count=12, 
            unit="units", description="Chainsaw for clearing tree falls"
        ),
        Resource(
            name="Barricade Set (10 units)", category="equipment", total_count=50, available_count=50, 
            unit="units", description="Standard crowd/traffic control barricade set"
        ),
        Resource(
            name="Fire Engine", category="equipment", total_count=6, available_count=6, 
            unit="units", description="Emergency fire engine suppression asset"
        ),
        Resource(
            name="Traffic Cone Set", category="equipment", total_count=100, available_count=100, 
            unit="units", description="Reflective safety traffic cones set"
        )
    ]
    
    db.add_all(defaults)
    db.commit()


class Incident(Base):
    __tablename__ = "incidents"
    
    id = Column(String, primary_key=True)
    reported_by = Column(String, nullable=False)
    reported_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    resolved_at = Column(DateTime, nullable=True)
    status = Column(String, nullable=False)  # "active" | "resolved"
    
    # Location
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    address = Column(String, nullable=False)
    junction = Column(String, nullable=False)
    zone = Column(String, nullable=False)
    corridor = Column(String, nullable=False)
    
    # Incident details
    event_cause = Column(String, nullable=False)
    priority = Column(String, nullable=False)
    description = Column(String, nullable=False)
    hour_of_day = Column(Integer, nullable=False)
    
    # AI prediction results
    predicted_duration_mins = Column(Float, nullable=False)
    severity_multiplier = Column(Float, nullable=False)
    jam_length_km = Column(Float, nullable=False)
    officers_needed = Column(Integer, nullable=False)
    barricade_points = Column(Integer, nullable=False)
    hazards_present = Column(String, nullable=False)      # JSON string of list
    special_assets_needed = Column(String, nullable=False) # JSON string of list
    spatial_resolution_method = Column(String, nullable=False)
    nearest_junction = Column(String, nullable=False)
    notes = Column(String, default="", nullable=True)



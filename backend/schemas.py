"""
Pydantic schemas for request / response validation.
"""
from __future__ import annotations

from enum import Enum
from typing import Optional
from datetime import datetime

from pydantic import BaseModel, Field


# ── Enums ─────────────────────────────────────────────────────────────────────

class WeatherCondition(str, Enum):
    clear      = "Clear"
    rain       = "Rain"
    heavy_rain = "Heavy Rain"
    fog        = "Fog"
    cloudy     = "Cloudy"


class DayOfWeek(str, Enum):
    monday    = "Monday"
    tuesday   = "Tuesday"
    wednesday = "Wednesday"
    thursday  = "Thursday"
    friday    = "Friday"
    saturday  = "Saturday"
    sunday    = "Sunday"


class RoadType(str, Enum):
    national_highway = "National Highway"
    state_highway    = "State Highway"
    arterial         = "Arterial Road"
    ring_road        = "Ring Road"
    inner_ring_road  = "Inner Ring Road"
    local            = "Local Road"


# ── Request ───────────────────────────────────────────────────────────────────

class PredictionRequest(BaseModel):
    """Input features required to generate a traffic incident prediction."""

    # Location
    location: str = Field(..., example="Silk Board Junction", description="Name of the junction / area")
    latitude:  Optional[float] = Field(None, example=12.9176, description="Latitude (optional)")
    longitude: Optional[float] = Field(None, example=77.6237, description="Longitude (optional)")
    road_type: RoadType = Field(RoadType.arterial, description="Type of road at the location")

    # Time
    hour:         int         = Field(..., ge=0, le=23,  example=8,  description="Hour of the day (0-23)")
    day_of_week:  DayOfWeek   = Field(..., example="Monday",         description="Day of the week")
    is_peak_hour: bool        = Field(..., example=True,             description="Is this a peak traffic hour?")
    is_holiday:   bool        = Field(False,                         description="Is today a public holiday?")

    # Weather
    weather:     WeatherCondition = Field(WeatherCondition.clear,    description="Current weather condition")
    visibility:  Optional[float]  = Field(None, ge=0, le=10, example=8.0, description="Visibility in km")
    rainfall_mm: Optional[float]  = Field(None, ge=0, example=0.0,  description="Rainfall in mm (last hour)")

    # Road conditions
    vehicles_per_hour:   Optional[int]   = Field(None, ge=0, example=3500, description="Estimated traffic volume")
    road_works_active:   bool            = Field(False,  description="Are road works currently active nearby?")
    accident_last_24h:   bool            = Field(False,  description="Was there an accident here in the last 24 h?")

    # Optional description for LLM enrichment
    description: Optional[str] = Field(None, example="Heavy waterlogging reported near underpass",
                                       description="Free-text description for LLM severity scoring")

    class Config:
        json_schema_extra = {
            "example": {
                "location": "Silk Board Junction",
                "latitude": 12.9176,
                "longitude": 77.6237,
                "road_type": "Arterial Road",
                "hour": 8,
                "day_of_week": "Monday",
                "is_peak_hour": True,
                "is_holiday": False,
                "weather": "Rain",
                "visibility": 4.5,
                "rainfall_mm": 12.0,
                "vehicles_per_hour": 4200,
                "road_works_active": False,
                "accident_last_24h": True,
                "description": "Heavy waterlogging near underpass causing major snarls",
            }
        }


# ── Response ──────────────────────────────────────────────────────────────────

class PredictionResponse(BaseModel):
    """Full prediction output returned to the frontend."""

    location:          str
    predicted_cause:   str   = Field(..., description="Predicted cause of the incident (label-decoded)")
    predicted_priority: str  = Field(..., description="Predicted priority level (Low / Medium / High / Critical)")

    # NGBoost probabilistic outputs
    severity_score:    float = Field(..., ge=0, le=10, description="Predicted severity score (0-10)")
    confidence:        float = Field(..., ge=0, le=1,  description="Model confidence (0-1)")
    severity_lower:    float = Field(..., description="Lower bound of 90% prediction interval")
    severity_upper:    float = Field(..., description="Upper bound of 90% prediction interval")

    # LLM-enriched fields
    llm_severity:      Optional[float] = Field(None, description="LLM-assessed severity (0-10)")
    llm_summary:       Optional[str]   = Field(None, description="LLM-generated plain-language summary")
    llm_recommendation: Optional[str] = Field(None, description="LLM-generated route / action recommendation")

    # Meta
    model_version:     str  = "ngboost-v1"
    status:            str  = "success"


class HealthResponse(BaseModel):
    status: str


# ── New Spatial Prediction Models ─────────────────────────────────────────────

class IncidentInput(BaseModel):
    event_cause: str
    priority: str
    hour_of_day: int
    description: str
    
    # Location — always required for spatial lookup
    latitude: float
    longitude: float
    
    # Spatial embeddings — OPTIONAL, backend fills these if missing
    spatial_emb_0: Optional[float] = None
    spatial_emb_1: Optional[float] = None
    spatial_emb_2: Optional[float] = None
    spatial_emb_3: Optional[float] = None
    spatial_emb_4: Optional[float] = None
    spatial_emb_5: Optional[float] = None
    spatial_emb_6: Optional[float] = None
    spatial_emb_7: Optional[float] = None
    spatial_emb_8: Optional[float] = None
    spatial_emb_9: Optional[float] = None
    spatial_emb_10: Optional[float] = None
    spatial_emb_11: Optional[float] = None
    spatial_emb_12: Optional[float] = None
    spatial_emb_13: Optional[float] = None
    spatial_emb_14: Optional[float] = None
    spatial_emb_15: Optional[float] = None
    
    # Historical features — OPTIONAL, backend fills if missing
    historical_incident_count: Optional[float] = None
    historical_median_duration: Optional[float] = None
    
    # Display fields
    address: str = ""
    junction: str = ""
    zone: str = ""
    corridor: str = ""


class SuggestedResource(BaseModel):
    resource_name: str
    resource_id: int
    quantity_suggested: int
    quantity_available: int
    status: str


class PredictionOutput(BaseModel):
    predicted_duration_mins: float
    severity_multiplier: float
    jam_length_km: float
    officers_needed: int
    barricade_points: int
    hazards_present: list[str]
    special_assets_needed: list[str]
    latitude: float
    longitude: float
    address: str
    junction: str
    zone: str
    corridor: str
    priority: str
    event_cause: str
    
    # NEW: tells frontend how spatial embeddings were resolved
    spatial_resolution_method: str  
    # Values: "exact_match" | "proximity_average" | "global_average"
    nearest_junction: str           
    # Name of matched/nearest junction or "global_average"
    distance_to_nearest_m: float    
    # Distance in metres to nearest known junction
    
    suggested_resources: list[SuggestedResource]
    resource_shortage: bool


class BatchIncidentInput(BaseModel):
    incidents: list[IncidentInput]


class BatchPredictionOutput(BaseModel):
    results: list[PredictionOutput]
    total_officers_needed: int
    high_priority_count: int


# ── Resource Management Schemas ───────────────────────────────────────────────

class ResourceItem(BaseModel):
    id: int
    name: str
    category: str
    total_count: int
    available_count: int
    unit: str
    allocated_count: int


class ResourceListResponse(BaseModel):
    personnel: list[ResourceItem]
    vehicle: list[ResourceItem]
    equipment: list[ResourceItem]


class AllocationItemRequest(BaseModel):
    resource_id: int
    quantity: int = Field(..., ge=1)


class AllocateRequest(BaseModel):
    incident_id: str
    incident_address: str
    allocations: list[AllocationItemRequest]
    notes: Optional[str] = None


class AllocateResponse(BaseModel):
    allocation_ids: list[int]
    updated_resources: ResourceListResponse


class ReleasedResourceItem(BaseModel):
    resource_id: int
    name: str
    quantity_released: int


class ReleaseResponse(BaseModel):
    incident_id: str
    released_allocations_count: int
    released_resources: list[ReleasedResourceItem]


class ActiveAllocationItem(BaseModel):
    resource_name: str
    quantity: int
    allocated_at: datetime


class ResourceSummaryResponse(BaseModel):
    total_officers: int
    available_officers: int
    deployed_officers: int
    total_equipment_units: int
    available_equipment_units: int
    active_allocations_count: int
    incidents_with_resources: list[str]


class UpdateResourceTotalRequest(BaseModel):
    total_count: int = Field(..., ge=0)


class IncidentReportRequest(IncidentInput):
    reported_by: str


class IncidentResponse(BaseModel):
    id: str
    reported_by: str
    reported_at: datetime
    resolved_at: Optional[datetime] = None
    status: str
    
    # Location
    latitude: float
    longitude: float
    address: str
    junction: str
    zone: str
    corridor: str
    
    # Incident details
    event_cause: str
    priority: str
    description: str
    hour_of_day: int
    
    # AI prediction results
    predicted_duration_mins: float
    severity_multiplier: float
    jam_length_km: float
    officers_needed: int
    barricade_points: int
    hazards_present: list[str]
    special_assets_needed: list[str]
    spatial_resolution_method: str
    nearest_junction: str
    notes: Optional[str] = ""

    class Config:
        orm_mode = True
        from_attributes = True


class UpdateIncidentRequest(BaseModel):
    status: Optional[str] = None
    notes: Optional[str] = None


class CreateResourceRequest(BaseModel):
    name: str
    category: str
    total_count: int
    unit: str
    description: Optional[str] = None


class ActiveDeploymentItem(BaseModel):
    id: int
    incident_id: str
    incident_address: str
    resource_name: str
    quantity: int
    allocated_at: datetime



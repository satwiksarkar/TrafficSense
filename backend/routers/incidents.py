import json
import random
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import desc
from sqlalchemy.orm import Session

from database import get_db
from db_models import Incident, Resource, Allocation
from websocket_manager import manager
from schemas import IncidentReportRequest, IncidentResponse, UpdateIncidentRequest
from routers.predict import run_prediction

router = APIRouter()

# Helper function to map database Incident model to dictionary output matching IncidentResponse
def format_incident(inc: Incident) -> dict:
    try:
        hazards = json.loads(inc.hazards_present) if inc.hazards_present else []
    except Exception:
        hazards = []
    try:
        assets = json.loads(inc.special_assets_needed) if inc.special_assets_needed else []
    except Exception:
        assets = []

    return {
        "id": inc.id,
        "reported_by": inc.reported_by,
        "reported_at": inc.reported_at,
        "resolved_at": inc.resolved_at,
        "status": inc.status,
        "latitude": inc.latitude,
        "longitude": inc.longitude,
        "address": inc.address,
        "junction": inc.junction,
        "zone": inc.zone,
        "corridor": inc.corridor,
        "event_cause": inc.event_cause,
        "priority": inc.priority,
        "description": inc.description,
        "hour_of_day": inc.hour_of_day,
        "predicted_duration_mins": inc.predicted_duration_mins,
        "severity_multiplier": inc.severity_multiplier,
        "jam_length_km": inc.jam_length_km,
        "officers_needed": inc.officers_needed,
        "barricade_points": inc.barricade_points,
        "hazards_present": hazards,
        "special_assets_needed": assets,
        "spatial_resolution_method": inc.spatial_resolution_method,
        "nearest_junction": inc.nearest_junction,
        "notes": inc.notes or "",
    }


# ── POST /incidents/report ────────────────────────────────────────────────────
@router.post("/report", response_model=IncidentResponse, status_code=status.HTTP_201_CREATED, summary="Report a new incident")
async def report_incident(payload: IncidentReportRequest, db: Session = Depends(get_db)):
    # 1. Generate incident ID: INC_YYYYMMDD_XXX
    timestamp = datetime.utcnow().strftime("%Y%m%d")
    random_suffix = f"{random.randint(100, 999)}"
    incident_id = f"INC_{timestamp}_{random_suffix}"

    # Verify uniqueness in DB just in case
    while db.query(Incident).filter(Incident.id == incident_id).first() is not None:
         random_suffix = f"{random.randint(100, 999)}"
         incident_id = f"INC_{timestamp}_{random_suffix}"

    try:
        # 2. Run prediction pipeline
        pred = await run_prediction(payload, db)
        
        # 3. Create database instance
        new_inc = Incident(
            id=incident_id,
            reported_by=payload.reported_by,
            reported_at=datetime.utcnow(),
            resolved_at=None,
            status="active",
            latitude=payload.latitude,
            longitude=payload.longitude,
            address=pred.address or payload.address or "",
            junction=pred.junction or payload.junction or "",
            zone=pred.zone or payload.zone or "",
            corridor=pred.corridor or payload.corridor or "",
            event_cause=payload.event_cause,
            priority=payload.priority,
            description=payload.description,
            hour_of_day=payload.hour_of_day,
            predicted_duration_mins=pred.predicted_duration_mins,
            severity_multiplier=pred.severity_multiplier,
            jam_length_km=pred.jam_length_km,
            officers_needed=pred.officers_needed,
            barricade_points=pred.barricade_points,
            hazards_present=json.dumps(pred.hazards_present),
            special_assets_needed=json.dumps(pred.special_assets_needed),
            spatial_resolution_method=pred.spatial_resolution_method,
            nearest_junction=pred.nearest_junction
        )
        
        db.add(new_inc)
        db.commit()
        db.refresh(new_inc)
        
        formatted = format_incident(new_inc)

        # 4. Broadcast to all WebSocket clients
        await manager.broadcast({
            "type": "NEW_INCIDENT",
            "incident": formatted
        })
        
        return formatted
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


# ── POST /incidents/resolve/{incident_id} ─────────────────────────────────────
@router.post("/resolve/{incident_id}", response_model=IncidentResponse, summary="Resolve an incident and release its resources")
async def resolve_incident(incident_id: str, db: Session = Depends(get_db)):
    inc = db.query(Incident).filter(Incident.id == incident_id).first()
    if not inc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Incident {incident_id} not found")
    
    if inc.status == "resolved":
        return format_incident(inc)
    
    try:
        # 1. Update status
        inc.status = "resolved"
        inc.resolved_at = datetime.utcnow()
        
        # 2. Release allocated resources
        active_allocations = db.query(Allocation).filter(
            Allocation.incident_id == incident_id,
            Allocation.status == "active"
        ).all()
        
        now = datetime.utcnow()
        for alloc in active_allocations:
            resource = db.query(Resource).filter(Resource.id == alloc.resource_id).first()
            if resource:
                resource.available_count += alloc.quantity_allocated
            alloc.status = "released"
            alloc.released_at = now
            
        db.commit()
        db.refresh(inc)
        
        formatted = format_incident(inc)

        # 3. Broadcast to all WebSocket clients
        await manager.broadcast({
            "type": "INCIDENT_RESOLVED",
            "incident_id": incident_id
        })
        
        return formatted
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


# ── GET /incidents/active ─────────────────────────────────────────────────────
@router.get("/active", response_model=list[IncidentResponse], summary="Get all active incidents")
def get_active_incidents(db: Session = Depends(get_db)):
    active_incidents = db.query(Incident).filter(Incident.status == "active").order_by(desc(Incident.reported_at)).all()
    return [format_incident(inc) for inc in active_incidents]


# ── GET /incidents/history ────────────────────────────────────────────────────
@router.get("/history", response_model=list[IncidentResponse], summary="Get historical incidents with pagination and filtering")
def get_incident_history(
    limit: int = 50,
    offset: int = 0,
    cause: Optional[str] = None,
    priority: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    query = db.query(Incident)
    
    if cause:
        query = query.filter(Incident.event_cause == cause)
    if priority:
        query = query.filter(Incident.priority == priority)
    if status and status.lower() != 'all':
        db_status = "active" if status.lower() in ("open", "active") else "resolved"
        query = query.filter(Incident.status == db_status)
        
    incidents = query.order_by(desc(Incident.reported_at)).offset(offset).limit(limit).all()
    return [format_incident(inc) for inc in incidents]


# ── PATCH /incidents/{incident_id} ────────────────────────────────────────────
@router.patch("/{incident_id}", response_model=IncidentResponse, summary="Update incident status and/or notes")
async def update_incident(incident_id: str, payload: UpdateIncidentRequest, db: Session = Depends(get_db)):
    inc = db.query(Incident).filter(Incident.id == incident_id).first()
    if not inc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Incident {incident_id} not found")
    
    try:
        if payload.status is not None:
            new_status = payload.status.lower()
            if new_status == "resolved" and inc.status != "resolved":
                inc.status = "resolved"
                inc.resolved_at = datetime.utcnow()
                # Release allocated resources
                active_allocations = db.query(Allocation).filter(
                    Allocation.incident_id == incident_id,
                    Allocation.status == "active"
                ).all()
                now = datetime.utcnow()
                for alloc in active_allocations:
                    resource = db.query(Resource).filter(Resource.id == alloc.resource_id).first()
                    if resource:
                        resource.available_count += alloc.quantity_allocated
                    alloc.status = "released"
                    alloc.released_at = now
            elif new_status != "resolved" and inc.status == "resolved":
                inc.status = payload.status
                inc.resolved_at = None
            else:
                inc.status = payload.status
        
        if payload.notes is not None:
            inc.notes = payload.notes
            
        db.commit()
        db.refresh(inc)
        
        formatted = format_incident(inc)
        
        # Broadcast the update to all clients
        await manager.broadcast({
            "type": "INCIDENT_UPDATED",
            "incident": formatted
        })
        
        return formatted
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))

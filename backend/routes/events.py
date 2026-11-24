"""Supply Chain Event routes"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from database import get_db, EventType, EventStatus
from models import (
    SupplyChainEventCreate, SupplyChainEventUpdate, SupplyChainEventResponse,
    EventData, HarvestData, ProcessingData, LogisticsData,
    PriceData, QualityData, RetailData
)
from crud import (
    create_event, get_event, get_events, get_events_by_crop,
    get_pending_review_events, get_committed_unanchored_events,
    commit_event, reject_event
)
import json

router = APIRouter(prefix="/events", tags=["events"])


@router.post("/", response_model=SupplyChainEventResponse, status_code=status.HTTP_201_CREATED)
def create_event_endpoint(event: SupplyChainEventCreate, db: Session = Depends(get_db)):
    """Create a new supply chain event"""
    # Validate event data based on event type
    _validate_event_data(event.event_type, event.data_json)
    return create_event(db, event)


def _validate_event_data(event_type: EventType, data_json: dict):
    """Validate event data against expected schema for the event type"""
    required_fields = {
        EventType.HARVEST: ["quantity_kg", "grade", "moisture_pct"],
        EventType.PROCESSING: ["input_quantity_kg", "output_quantity_kg", "processing_type", "grade_in", "grade_out"],
        EventType.LOGISTICS: ["quantity_kg", "transport_mode", "origin", "destination"],
        EventType.PRICE: ["price_cents", "quantity_kg", "price_type", "grade"],
        EventType.QUALITY: ["grade", "moisture_pct"],
        EventType.RETAIL: ["price_cents", "quantity_kg"],
    }

    missing = [f for f in required_fields.get(event_type, []) if f not in data_json]
    if missing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Missing required fields for {event_type.value}: {missing}"
        )


@router.get("/", response_model=List[SupplyChainEventResponse])
def list_events(
    crop_id: Optional[int] = Query(None),
    event_type: Optional[EventType] = Query(None),
    status: Optional[EventStatus] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db)
):
    """List events with optional filters"""
    return get_events(db, crop_id=crop_id, event_type=event_type, status=status, skip=skip, limit=limit)


@router.get("/crop/{crop_id}", response_model=List[SupplyChainEventResponse])
def get_crop_events(crop_id: int, db: Session = Depends(get_db)):
    """Get all events for a crop in chronological order"""
    return get_events_by_crop(db, crop_id)


@router.get("/{event_id}", response_model=SupplyChainEventResponse)
def get_event_endpoint(event_id: int, db: Session = Depends(get_db)):
    """Get a single event by ID"""
    event = get_event(db, event_id)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Event with id {event_id} not found"
        )
    return event


@router.get("/pending/review", response_model=List[SupplyChainEventResponse])
def get_pending_review_events_endpoint(db: Session = Depends(get_db)):
    """Get all events pending review (flagged by anomaly detection)"""
    return get_pending_review_events(db)


@router.get("/committed/unanchored", response_model=List[SupplyChainEventResponse])
def get_committed_unanchored_events_endpoint(
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db)
):
    """Get committed events not yet anchored to blockchain"""
    return get_committed_unanchored_events(db, limit=limit)


@router.patch("/{event_id}", response_model=SupplyChainEventResponse)
def update_event_endpoint(event_id: int, event_update: SupplyChainEventUpdate, db: Session = Depends(get_db)):
    """Update an event"""
    from crud import update_event
    event = update_event(db, event_id, event_update)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Event with id {event_id} not found"
        )
    return event


@router.post("/{event_id}/commit", response_model=SupplyChainEventResponse)
def commit_event_endpoint(event_id: int, db: Session = Depends(get_db)):
    """Mark an event as committed (after review acceptance)"""
    event = commit_event(db, event_id)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Event with id {event_id} not found"
        )
    return event


@router.post("/{event_id}/reject", response_model=SupplyChainEventResponse)
def reject_event_endpoint(event_id: int, db: Session = Depends(get_db)):
    """Reject an event"""
    event = reject_event(db, event_id)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Event with id {event_id} not found"
        )
    return event
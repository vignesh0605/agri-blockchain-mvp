"""Traceability routes - Consumer-facing traceability view"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.requests import Request

from database import get_db, EventStatus
from models import TraceResponse, TraceEventResponse, BlockchainAnchorResponse
from crud import get_crop, get_crop_by_batch_code, get_events_by_crop, get_latest_anchor
from anchor_service import get_anchor_service

router = APIRouter(prefix="/trace", tags=["trace"])
templates = Jinja2Templates(directory="backend/templates")


@router.get("/{crop_id}", response_model=TraceResponse)
def trace_crop(crop_id: int, db: Session = Depends(get_db)):
    """Get full traceability timeline for a crop"""
    crop = get_crop(db, crop_id)
    if not crop:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Crop with id {crop_id} not found"
        )

    events = get_events_by_crop(db, crop_id)
    event_responses = []

    for event in events:
        is_anomalous = event.anomaly_score > 30
        anchor_tx_hash = None
        if event.anchor_batch_id:
            from crud import get_anchor
            anchor = get_anchor(db, event.anchor_batch_id)
            if anchor:
                anchor_tx_hash = anchor.tx_hash

        event_responses.append(TraceEventResponse(
            event_id=event.id,
            event_type=event.event_type,
            actor_role=event.actor_role,
            actor_id=event.actor_id,
            timestamp=event.timestamp,
            location=event.location,
            data_json=event.data_json,
            status=event.status,
            anomaly_score=event.anomaly_score,
            is_anomalous=is_anomalous,
            anchor_tx_hash=anchor_tx_hash
        ))

    # Get latest anchor for this crop's events
    latest_anchor_obj = None
    anchored_events = [e for e in events if e.anchor_batch_id]
    if anchored_events:
        latest_anchor_obj = get_latest_anchor(db)

    return TraceResponse(
        crop_id=crop.id,
        batch_code=crop.batch_code,
        crop_name=crop.name,
        variety=crop.variety,
        farm_name=crop.farm.name,
        farm_location=crop.farm.location,
        events=event_responses,
        latest_anchor=latest_anchor_obj
    )


@router.get("/batch/{batch_code}", response_model=TraceResponse)
def trace_crop_by_batch(batch_code: str, db: Session = Depends(get_db)):
    """Get traceability by batch code (consumer-friendly)"""
    crop = get_crop_by_batch_code(db, batch_code)
    if not crop:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Crop with batch code {batch_code} not found"
        )
    return trace_crop(crop.id, db)


@router.get("/{crop_id}/html", response_class=HTMLResponse)
def trace_crop_html(request: Request, crop_id: int, db: Session = Depends(get_db)):
    """HTML traceability view for consumers"""
    crop = get_crop(db, crop_id)
    if not crop:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Crop with id {crop_id} not found"
        )

    events = get_events_by_crop(db, crop_id)

    # Check if any event is anchored
    is_verified = any(e.anchor_batch_id for e in events)
    anchor_info = None
    if is_verified:
        from crud import get_anchor
        anchor = get_anchor(db, events[0].anchor_batch_id) if events else None
        if anchor:
            anchor_info = {
                "tx_hash": anchor.tx_hash,
                "block_number": anchor.block_number,
                "batch_hash": anchor.batch_hash,
                "timestamp": anchor.timestamp
            }

    return templates.TemplateResponse("trace.html", {
        "request": request,
        "crop": crop,
        "events": events,
        "is_verified": is_verified,
        "anchor_info": anchor_info
    })


@router.get("/batch/{batch_code}/html", response_class=HTMLResponse)
def trace_crop_by_batch_html(request: Request, batch_code: str, db: Session = Depends(get_db)):
    """HTML traceability view by batch code"""
    crop = get_crop_by_batch_code(db, batch_code)
    if not crop:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Crop with batch code {batch_code} not found"
        )
    return trace_crop_html(request, crop.id, db)


@router.get("/verify/{event_id}")
def verify_event_integrity(event_id: int, db: Session = Depends(get_db)):
    """Verify data integrity of an event against blockchain anchor"""
    service = get_anchor_service()
    return service.verify_event(event_id)
"""Blockchain Anchor routes"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from database import get_db, AnchorStatus
from models import (
    BlockchainAnchorCreate, BlockchainAnchorResponse,
    VerificationResponse
)
from crud import (
    create_blockchain_anchor, get_anchor, get_anchor_by_batch_hash,
    get_latest_anchor, get_anchors, update_anchor_status
)
from anchor_service import get_anchor_service

router = APIRouter(prefix="/anchor", tags=["anchor"])


@router.post("/batch", response_model=BlockchainAnchorResponse, status_code=status.HTTP_201_CREATED)
def create_anchor_batch(
    anchor: BlockchainAnchorCreate,
    db: Session = Depends(get_db)
):
    """Create a new batch anchor from committed events"""
    service = get_anchor_service()
    anchor_obj = service.create_batch(max_events=len(anchor.event_ids))
    if not anchor_obj:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No events to anchor or batch creation failed"
        )
    return anchor_obj


@router.post("/batch/submit", response_model=BlockchainAnchorResponse)
def submit_anchor_batch(
    anchor_id: int,
    db: Session = Depends(get_db)
):
    """Submit a batch anchor to blockchain"""
    service = get_anchor_service()
    success = service.submit_batch(anchor_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to submit batch to blockchain"
        )
    anchor = get_anchor(db, anchor_id)
    return anchor


@router.post("/batch/auto", response_model=BlockchainAnchorResponse)
def auto_anchor_batch(
    max_events: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """Automatically create and submit a batch of committed unanchored events"""
    service = get_anchor_service()
    anchor = service.anchor_batch(max_events=max_events)
    if not anchor:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No events to anchor or anchoring failed"
        )
    return anchor


@router.get("/", response_model=List[BlockchainAnchorResponse])
def list_anchors(
    status: Optional[AnchorStatus] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db)
):
    """List all blockchain anchors"""
    query = db.query(BlockchainAnchor)
    if status:
        query = query.filter(BlockchainAnchor.status == status)
    return query.order_by(BlockchainAnchor.id.desc()).offset(skip).limit(limit).all()


@router.get("/latest", response_model=BlockchainAnchorResponse)
def get_latest_anchor_endpoint(db: Session = Depends(get_db)):
    """Get the most recent anchor"""
    anchor = get_latest_anchor(db)
    if not anchor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No anchors found"
        )
    return anchor


@router.get("/{anchor_id}", response_model=BlockchainAnchorResponse)
def get_anchor_endpoint(anchor_id: int, db: Session = Depends(get_db)):
    """Get an anchor by ID"""
    anchor = get_anchor(db, anchor_id)
    if not anchor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Anchor with id {anchor_id} not found"
        )
    return anchor


@router.get("/batch/{batch_hash}", response_model=BlockchainAnchorResponse)
def get_anchor_by_batch_hash_endpoint(batch_hash: str, db: Session = Depends(get_db)):
    """Get an anchor by batch hash"""
    anchor = get_anchor_by_batch_hash(db, batch_hash)
    if not anchor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Anchor with batch hash {batch_hash} not found"
        )
    return anchor


@router.get("/verify/{event_id}", response_model=VerificationResponse)
def verify_event_endpoint(event_id: int, db: Session = Depends(get_db)):
    """Verify an event's on-chain anchor proof"""
    service = get_anchor_service()
    result = service.verify_event(event_id)

    if not result.get("verified"):
        return VerificationResponse(
            event_id=event_id,
            data_hash="",
            is_verified=False
        )

    return VerificationResponse(**result)
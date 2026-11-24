"""CRUD operations for database models"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import desc, func, and_, or_

from database import (
    Farm, Crop, SupplyChainEvent, AnomalyFlag, ReviewQueue,
    BlockchainAnchor, EventStatus, AnomalyStatus, ReviewStatus, AnchorStatus, EventType
)
from models import (
    FarmCreate, FarmUpdate, CropCreate, CropUpdate,
    SupplyChainEventCreate, SupplyChainEventUpdate,
    ReviewQueueCreate, ReviewQueueUpdate,
    BlockchainAnchorCreate
)
import hashlib
import json


# ========== Hash Utilities ==========

def compute_data_hash(event_data: Dict[str, Any]) -> str:
    """Compute keccak256 hash of canonical JSON representation"""
    # Sort keys for canonical representation
    canonical_json = json.dumps(event_data, sort_keys=True, separators=(',', ':'))
    return "0x" + hashlib.sha256(canonical_json.encode()).hexdigest()


# ========== Farm CRUD ==========

def create_farm(db: Session, farm: FarmCreate) -> Farm:
    db_farm = Farm(**farm.model_dump())
    db.add(db_farm)
    db.commit()
    db.refresh(db_farm)
    return db_farm


def get_farm(db: Session, farm_id: int) -> Optional[Farm]:
    return db.query(Farm).filter(Farm.id == farm_id).first()


def get_farm_by_gstin(db: Session, gstin: str) -> Optional[Farm]:
    return db.query(Farm).filter(Farm.gstin == gstin).first()


def get_farm_by_wallet(db: Session, wallet_address: str) -> Optional[Farm]:
    return db.query(Farm).filter(Farm.wallet_address == wallet_address).first()


def get_farms(db: Session, skip: int = 0, limit: int = 100) -> List[Farm]:
    return db.query(Farm).offset(skip).limit(limit).all()


def update_farm(db: Session, farm_id: int, farm_update: FarmUpdate) -> Optional[Farm]:
    db_farm = get_farm(db, farm_id)
    if not db_farm:
        return None
    update_data = farm_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_farm, field, value)
    db_farm.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(db_farm)
    return db_farm


def delete_farm(db: Session, farm_id: int) -> bool:
    db_farm = get_farm(db, farm_id)
    if not db_farm:
        return False
    db.delete(db_farm)
    db.commit()
    return True


# ========== Crop CRUD ==========

def create_crop(db: Session, crop: CropCreate) -> Crop:
    db_crop = Crop(**crop.model_dump())
    db.add(db_crop)
    db.commit()
    db.refresh(db_crop)
    return db_crop


def get_crop(db: Session, crop_id: int) -> Optional[Crop]:
    return db.query(Crop).filter(Crop.id == crop_id).first()


def get_crop_by_batch_code(db: Session, batch_code: str) -> Optional[Crop]:
    return db.query(Crop).filter(Crop.batch_code == batch_code).first()


def get_crops(db: Session, farm_id: Optional[int] = None, skip: int = 0, limit: int = 100) -> List[Crop]:
    query = db.query(Crop)
    if farm_id:
        query = query.filter(Crop.farm_id == farm_id)
    return query.offset(skip).limit(limit).all()


def update_crop(db: Session, crop_id: int, crop_update: CropUpdate) -> Optional[Crop]:
    db_crop = get_crop(db, crop_id)
    if not db_crop:
        return None
    update_data = crop_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_crop, field, value)
    db_crop.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(db_crop)
    return db_crop


def delete_crop(db: Session, crop_id: int) -> bool:
    db_crop = get_crop(db, crop_id)
    if not db_crop:
        return False
    db.delete(db_crop)
    db.commit()
    return True


# ========== Supply Chain Event CRUD ==========

def create_event(db: Session, event: SupplyChainEventCreate) -> SupplyChainEvent:
    # Compute hash of event data
    event_dict = event.model_dump()
    data_hash = compute_data_hash(event_dict)

    db_event = SupplyChainEvent(
        **event_dict,
        data_hash=data_hash,
        status=EventStatus.PENDING
    )
    db.add(db_event)
    db.commit()
    db.refresh(db_event)
    return db_event


def get_event(db: Session, event_id: int) -> Optional[SupplyChainEvent]:
    return db.query(SupplyChainEvent).filter(SupplyChainEvent.id == event_id).first()


def get_events(
    db: Session,
    crop_id: Optional[int] = None,
    event_type: Optional[EventType] = None,
    status: Optional[EventStatus] = None,
    skip: int = 0,
    limit: int = 100
) -> List[SupplyChainEvent]:
    query = db.query(SupplyChainEvent)
    if crop_id:
        query = query.filter(SupplyChainEvent.crop_id == crop_id)
    if event_type:
        query = query.filter(SupplyChainEvent.event_type == event_type)
    if status:
        query = query.filter(SupplyChainEvent.status == status)
    return query.order_by(desc(SupplyChainEvent.timestamp)).offset(skip).limit(limit).all()


def get_events_by_crop(db: Session, crop_id: int) -> List[SupplyChainEvent]:
    return db.query(SupplyChainEvent).filter(
        SupplyChainEvent.crop_id == crop_id
    ).order_by(SupplyChainEvent.timestamp).all()


def update_event(db: Session, event_id: int, event_update: SupplyChainEventUpdate) -> Optional[SupplyChainEvent]:
    db_event = get_event(db, event_id)
    if not db_event:
        return None
    update_data = event_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_event, field, value)
    db_event.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(db_event)
    return db_event


def commit_event(db: Session, event_id: int) -> Optional[SupplyChainEvent]:
    return update_event(db, event_id, SupplyChainEventUpdate(status=EventStatus.COMMITTED))


def reject_event(db: Session, event_id: int) -> Optional[SupplyChainEvent]:
    return update_event(db, event_id, SupplyChainEventUpdate(status=EventStatus.REJECTED))


def get_pending_review_events(db: Session) -> List[SupplyChainEvent]:
    return db.query(SupplyChainEvent).filter(
        SupplyChainEvent.status == EventStatus.FLAGGED
    ).order_by(desc(SupplyChainEvent.anomaly_score)).all()


def get_committed_unanchored_events(db: Session, limit: int = 100) -> List[SupplyChainEvent]:
    return db.query(SupplyChainEvent).filter(
        SupplyChainEvent.status == EventStatus.COMMITTED,
        SupplyChainEvent.anchor_batch_id.is_(None)
    ).order_by(SupplyChainEvent.timestamp).limit(limit).all()


# ========== Anomaly Flag CRUD ==========

def create_anomaly_flag(
    db: Session,
    event_id: int,
    score: int,
    features: Dict[str, Any],
    threshold: int = 30,
    model_version: str = "isolation_forest_v1"
) -> AnomalyFlag:
    db_flag = AnomalyFlag(
        event_id=event_id,
        score=score,
        features_json=features,
        threshold=threshold,
        model_version=model_version,
        status=AnomalyStatus.PENDING
    )
    db.add(db_flag)
    db.commit()
    db.refresh(db_flag)
    return db_flag


def get_anomaly_flag(db: Session, event_id: int) -> Optional[AnomalyFlag]:
    return db.query(AnomalyFlag).filter(AnomalyFlag.event_id == event_id).first()


def update_anomaly_flag_status(
    db: Session,
    event_id: int,
    status: AnomalyStatus,
    admin_notes: Optional[str] = None,
    reviewed_by: Optional[str] = None
) -> Optional[AnomalyFlag]:
    db_flag = get_anomaly_flag(db, event_id)
    if not db_flag:
        return None
    db_flag.status = status
    if admin_notes:
        db_flag.admin_notes = admin_notes
    if reviewed_by:
        db_flag.reviewed_by = reviewed_by
    db_flag.reviewed_at = datetime.utcnow()
    db.commit()
    db.refresh(db_flag)
    return db_flag


# ========== Review Queue CRUD ==========

def create_review_queue(db: Session, review: ReviewQueueCreate) -> ReviewQueue:
    # Calculate priority based on anomaly score
    anomaly_flag = None
    if review.anomaly_flag_id:
        anomaly_flag = db.query(AnomalyFlag).filter(AnomalyFlag.id == review.anomaly_flag_id).first()
    priority = anomaly_flag.score if anomaly_flag else 0

    db_review = ReviewQueue(
        **review.model_dump(),
        priority=priority,
        status=ReviewStatus.PENDING
    )
    db.add(db_review)
    db.commit()
    db.refresh(db_review)
    return db_review


def get_review(db: Session, review_id: int) -> Optional[ReviewQueue]:
    return db.query(ReviewQueue).filter(ReviewQueue.id == review_id).first()


def get_review_by_event(db: Session, event_id: int) -> Optional[ReviewQueue]:
    return db.query(ReviewQueue).filter(ReviewQueue.event_id == event_id).first()


def get_pending_reviews(db: Session, skip: int = 0, limit: int = 100) -> List[ReviewQueue]:
    return db.query(ReviewQueue).filter(
        ReviewQueue.status.in_([ReviewStatus.PENDING, ReviewStatus.IN_PROGRESS])
    ).order_by(desc(ReviewQueue.priority), ReviewQueue.created_at).offset(skip).limit(limit).all()


def update_review(db: Session, review_id: int, review_update: ReviewQueueUpdate) -> Optional[ReviewQueue]:
    db_review = get_review(db, review_id)
    if not db_review:
        return None
    update_data = review_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_review, field, value)
    db_review.updated_at = datetime.utcnow()
    if review_update.status in [ReviewStatus.ACCEPTED, ReviewStatus.REJECTED]:
        db_review.completed_at = datetime.utcnow()
    db.commit()
    db.refresh(db_review)
    return db_review


# ========== Blockchain Anchor CRUD ==========

def create_blockchain_anchor(db: Session, anchor: BlockchainAnchorCreate) -> BlockchainAnchor:
    db_anchor = BlockchainAnchor(
        batch_hash="",  # Will be set later
        merkle_root="",  # Will be set later
        event_ids_json=anchor.event_ids,
        status=AnchorStatus.PENDING,
        event_count=len(anchor.event_ids)
    )
    db.add(db_anchor)
    db.commit()
    db.refresh(db_anchor)
    return db_anchor


def get_anchor(db: Session, anchor_id: int) -> Optional[BlockchainAnchor]:
    return db.query(BlockchainAnchor).filter(BlockchainAnchor.id == anchor_id).first()


def get_anchor_by_batch_hash(db: Session, batch_hash: str) -> Optional[BlockchainAnchor]:
    return db.query(BlockchainAnchor).filter(BlockchainAnchor.batch_hash == batch_hash).first()


def get_latest_anchor(db: Session) -> Optional[BlockchainAnchor]:
    return db.query(BlockchainAnchor).order_by(desc(BlockchainAnchor.id)).first()


def get_anchors(db: Session, skip: int = 0, limit: int = 100) -> List[BlockchainAnchor]:
    return db.query(BlockchainAnchor).order_by(desc(BlockchainAnchor.id)).offset(skip).limit(limit).all()


def update_anchor_status(
    db: Session,
    anchor_id: int,
    status: AnchorStatus,
    tx_hash: Optional[str] = None,
    block_number: Optional[int] = None,
    batch_hash: Optional[str] = None,
    merkle_root: Optional[str] = None,
    prev_batch_hash: Optional[str] = None,
    error_message: Optional[str] = None
) -> Optional[BlockchainAnchor]:
    db_anchor = get_anchor(db, anchor_id)
    if not db_anchor:
        return None
    db_anchor.status = status
    if tx_hash:
        db_anchor.tx_hash = tx_hash
    if block_number:
        db_anchor.block_number = block_number
    if batch_hash:
        db_anchor.batch_hash = batch_hash
    if merkle_root:
        db_anchor.merkle_root = merkle_root
    if prev_batch_hash:
        db_anchor.prev_batch_hash = prev_batch_hash
    if error_message:
        db_anchor.error_message = error_message
    db.commit()
    db.refresh(db_anchor)
    return db_anchor


def assign_events_to_anchor(db: Session, event_ids: List[int], anchor_id: int) -> int:
    updated = db.query(SupplyChainEvent).filter(
        SupplyChainEvent.id.in_(event_ids)
    ).update({SupplyChainEvent.anchor_batch_id: anchor_id}, synchronize_session=False)
    db.commit()
    return updated
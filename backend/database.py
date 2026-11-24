"""SQLAlchemy database models and session management"""

from datetime import datetime
from typing import Optional, List
from sqlalchemy import (
    create_engine, Column, Integer, String, Text, DateTime,
    Float, ForeignKey, Enum as SQLEnum, Index, JSON, Boolean
)
from sqlalchemy.orm import declarative_base, sessionmaker, relationship, Session
from sqlalchemy.dialects.sqlite import JSON as SQLiteJSON
import json
import enum

from config import settings

# Create engine
engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False},
    echo=False  # Set to True for SQL debugging
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


class EventStatus(str, enum.Enum):
    PENDING = "pending"
    FLAGGED = "flagged"
    COMMITTED = "committed"
    REJECTED = "rejected"


class AnomalyStatus(str, enum.Enum):
    PENDING = "pending"
    ADMIN_REVIEW = "admin_review"
    ACCEPTED = "accepted"
    REJECTED = "rejected"


class ReviewStatus(str, enum.Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    NEEDS_MORE_INFO = "needs_more_info"


class AnchorStatus(str, enum.Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    FAILED = "failed"


class EventType(str, enum.Enum):
    HARVEST = "harvest"
    PROCESSING = "processing"
    LOGISTICS = "logistics"
    PRICE = "price"
    QUALITY = "quality"
    RETAIL = "retail"


class Farm(Base):
    __tablename__ = "farms"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    location = Column(String(500), nullable=False)
    gstin = Column(String(50), unique=True, index=True)  # GSTIN for India
    wallet_address = Column(String(42), unique=True, index=True)  # Ethereum address
    contact_email = Column(String(255))
    contact_phone = Column(String(50))
    certifications = Column(SQLiteJSON, default=list)  # List of certification strings
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    crops = relationship("Crop", back_populates="farm", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Farm(id={self.id}, name='{self.name}')>"


class Crop(Base):
    __tablename__ = "crops"

    id = Column(Integer, primary_key=True, index=True)
    farm_id = Column(Integer, ForeignKey("farms.id"), nullable=False, index=True)
    name = Column(String(100), nullable=False)  # e.g., "Tomato"
    variety = Column(String(100))  # e.g., "Roma"
    batch_code = Column(String(50), unique=True, index=True)  # e.g., "TOM-2026-001"
    planting_date = Column(DateTime, nullable=False)
    harvest_window_start = Column(DateTime)
    harvest_window_end = Column(DateTime)
    expected_yield_kg = Column(Float)
    certifications = Column(SQLiteJSON, default=list)  # Organic, GAP, etc.
    metadata_json = Column(SQLiteJSON, default=dict)  # Additional flexible fields
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    farm = relationship("Farm", back_populates="crops")
    events = relationship("SupplyChainEvent", back_populates="crop", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Crop(id={self.id}, batch_code='{self.batch_code}', name='{self.name}')>"


class SupplyChainEvent(Base):
    __tablename__ = "supply_chain_events"

    id = Column(Integer, primary_key=True, index=True)
    crop_id = Column(Integer, ForeignKey("crops.id"), nullable=False, index=True)
    event_type = Column(SQLEnum(EventType), nullable=False, index=True)
    actor_role = Column(String(100), nullable=False)  # farmer, processor, transporter, wholesaler, retailer
    actor_id = Column(String(100), index=True)  # Reference to actor (wallet, ID, etc.)
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    location = Column(String(500))  # GPS coordinates or location name
    data_json = Column(SQLiteJSON, default=dict, nullable=False)  # All event-specific data

    # Status and anomaly
    status = Column(SQLEnum(EventStatus), default=EventStatus.PENDING, nullable=False, index=True)
    anomaly_score = Column(Integer, default=0)  # 0-100
    review_id = Column(Integer, ForeignKey("review_queue.id"), nullable=True)

    # Hash for blockchain anchoring
    data_hash = Column(String(66), index=True)  # keccak256 hash (0x + 64 hex chars)

    # Anchoring info
    anchor_batch_id = Column(Integer, ForeignKey("blockchain_anchors.id"), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    crop = relationship("Crop", back_populates="events")
    anomaly_flag = relationship("AnomalyFlag", back_populates="event", uselist=False, cascade="all, delete-orphan")
    review = relationship("ReviewQueue", back_populates="event")

    # Composite indexes for common queries
    __table_args__ = (
        Index('ix_crop_timestamp', 'crop_id', 'timestamp'),
        Index('ix_status_timestamp', 'status', 'timestamp'),
        Index('ix_event_type_crop', 'event_type', 'crop_id'),
    )

    def __repr__(self):
        return f"<SupplyChainEvent(id={self.id}, crop_id={self.crop_id}, type='{self.event_type}', status='{self.status}')>"


class AnomalyFlag(Base):
    __tablename__ = "anomaly_flags"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, ForeignKey("supply_chain_events.id"), unique=True, nullable=False, index=True)
    score = Column(Integer, nullable=False)  # 0-100
    features_json = Column(SQLiteJSON, default=dict)  # Feature contributions for explainability
    threshold = Column(Integer, default=30)  # Threshold used for flagging
    model_version = Column(String(50), default="isolation_forest_v1")
    status = Column(SQLEnum(AnomalyStatus), default=AnomalyStatus.PENDING, nullable=False, index=True)
    admin_notes = Column(Text)
    reviewed_by = Column(String(100))  # Admin identifier
    reviewed_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    event = relationship("SupplyChainEvent", back_populates="anomaly_flag")

    def __repr__(self):
        return f"<AnomalyFlag(id={self.id}, event_id={self.event_id}, score={self.score}, status='{self.status}')>"


class ReviewQueue(Base):
    __tablename__ = "review_queue"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, ForeignKey("supply_chain_events.id"), nullable=False, index=True)
    anomaly_flag_id = Column(Integer, ForeignKey("anomaly_flags.id"), nullable=True, index=True)
    priority = Column(Integer, default=0)  # Higher = more urgent
    assigned_to = Column(String(100))  # Admin user
    status = Column(SQLEnum(ReviewStatus), default=ReviewStatus.PENDING, nullable=False, index=True)
    action = Column(String(50))  # accepted, rejected, needs_more_info
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = Column(DateTime)

    # Relationships
    event = relationship("SupplyChainEvent", back_populates="review")
    anomaly_flag = relationship("AnomalyFlag")

    def __repr__(self):
        return f"<ReviewQueue(id={self.id}, event_id={self.event_id}, status='{self.status}')>"


class BlockchainAnchor(Base):
    __tablename__ = "blockchain_anchors"

    id = Column(Integer, primary_key=True, index=True)
    batch_hash = Column(String(66), unique=True, nullable=False, index=True)  # keccak256
    merkle_root = Column(String(66), nullable=False)  # Merkle root of event hashes
    event_ids_json = Column(SQLiteJSON, default=list)  # List of event IDs in this batch
    tx_hash = Column(String(66), index=True)  # Transaction hash on Anvil
    block_number = Column(Integer, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    status = Column(SQLEnum(AnchorStatus), default=AnchorStatus.PENDING, nullable=False, index=True)
    event_count = Column(Integer, default=0)
    prev_batch_hash = Column(String(66), nullable=True)  # Chain to previous batch
    error_message = Column(Text)  # If failed

    # Relationships
    events = relationship("SupplyChainEvent", foreign_keys=[SupplyChainEvent.anchor_batch_id])

    def __repr__(self):
        return f"<BlockchainAnchor(id={self.id}, batch_hash='{self.batch_hash[:10]}...', tx_hash='{self.tx_hash[:10] if self.tx_hash else None}...')>"


def get_db() -> Session:
    """Dependency for FastAPI to get DB session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Initialize database - create all tables"""
    Base.metadata.create_all(bind=engine)
    print("Database tables created successfully")


def drop_db():
    """Drop all tables - use with caution!"""
    Base.metadata.drop_all(bind=engine)
    print("Database tables dropped")


if __name__ == "__main__":
    init_db()
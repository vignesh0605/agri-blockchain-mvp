"""Pydantic models for API request/response validation"""

from datetime import datetime
from typing import Optional, List, Dict, Any, Union
from pydantic import BaseModel, Field, EmailStr, validator
from enum import Enum


class EventType(str, Enum):
    HARVEST = "harvest"
    PROCESSING = "processing"
    LOGISTICS = "logistics"
    PRICE = "price"
    QUALITY = "quality"
    RETAIL = "retail"


class EventStatus(str, Enum):
    PENDING = "pending"
    FLAGGED = "flagged"
    COMMITTED = "committed"
    REJECTED = "rejected"


class AnomalyStatus(str, Enum):
    PENDING = "pending"
    ADMIN_REVIEW = "admin_review"
    ACCEPTED = "accepted"
    REJECTED = "rejected"


class ReviewStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    NEEDS_MORE_INFO = "needs_more_info"


class AnchorStatus(str, Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    FAILED = "failed"


# Farm models
class FarmBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    location: str = Field(..., min_length=1, max_length=500)
    gstin: Optional[str] = Field(None, max_length=50)
    wallet_address: Optional[str] = Field(None, pattern=r"^0x[a-fA-F0-9]{40}$")
    contact_email: Optional[EmailStr] = None
    contact_phone: Optional[str] = Field(None, max_length=50)
    certifications: List[str] = []


class FarmCreate(FarmBase):
    pass


class FarmUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    location: Optional[str] = Field(None, min_length=1, max_length=500)
    gstin: Optional[str] = Field(None, max_length=50)
    wallet_address: Optional[str] = Field(None, pattern=r"^0x[a-fA-F0-9]{40}$")
    contact_email: Optional[EmailStr] = None
    contact_phone: Optional[str] = Field(None, max_length=50)
    certifications: Optional[List[str]] = None


class FarmResponse(FarmBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Crop models
class CropBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    variety: Optional[str] = Field(None, max_length=100)
    batch_code: str = Field(..., min_length=1, max_length=50)
    planting_date: datetime
    harvest_window_start: Optional[datetime] = None
    harvest_window_end: Optional[datetime] = None
    expected_yield_kg: Optional[float] = Field(None, ge=0)
    certifications: List[str] = []
    metadata_json: Dict[str, Any] = {}


class CropCreate(CropBase):
    farm_id: int


class CropUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    variety: Optional[str] = Field(None, max_length=100)
    batch_code: Optional[str] = Field(None, min_length=1, max_length=50)
    planting_date: Optional[datetime] = None
    harvest_window_start: Optional[datetime] = None
    harvest_window_end: Optional[datetime] = None
    expected_yield_kg: Optional[float] = Field(None, ge=0)
    certifications: Optional[List[str]] = None
    metadata_json: Optional[Dict[str, Any]] = None


class CropResponse(CropBase):
    id: int
    farm_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Supply Chain Event models
class EventDataBase(BaseModel):
    """Base for event-specific data - extend for each event type"""
    pass


class HarvestData(EventDataBase):
    quantity_kg: float = Field(..., ge=0)
    grade: str = Field(..., pattern=r"^[A-D]$")  # A, B, C, D
    moisture_pct: float = Field(..., ge=0, le=100)
    harvest_method: Optional[str] = None  # manual, mechanical
    field_id: Optional[str] = None


class ProcessingData(EventDataBase):
    input_quantity_kg: float = Field(..., ge=0)
    output_quantity_kg: float = Field(..., ge=0)
    processing_type: str  # washing, sorting, packaging, milling
    grade_in: str = Field(..., pattern=r"^[A-D]$")
    grade_out: str = Field(..., pattern=r"^[A-D]$")
    facility_id: Optional[str] = None
    batch_ids_in: List[str] = []


class LogisticsData(EventDataBase):
    quantity_kg: float = Field(..., ge=0)
    transport_mode: str  # truck, rail, ship, air
    temperature_c: Optional[float] = None
    humidity_pct: Optional[float] = None
    distance_km: Optional[float] = None
    vehicle_id: Optional[str] = None
    driver_id: Optional[str] = None
    origin: str
    destination: str


class PriceData(EventDataBase):
    price_cents: int = Field(..., ge=0)  # Price in cents (e.g., 1500 = $15.00)
    currency: str = "INR"
    price_type: str  # wholesale, retail, farm_gate
    quantity_kg: float = Field(..., ge=0)
    market_id: Optional[str] = None
    grade: str = Field(..., pattern=r"^[A-D]$")


class QualityData(EventDataBase):
    grade: str = Field(..., pattern=r"^[A-D]$")
    moisture_pct: float = Field(..., ge=0, le=100)
    size_mm: Optional[float] = None
    color_score: Optional[int] = Field(None, ge=1, le=10)
    firmness: Optional[int] = Field(None, ge=1, le=10)
    defects_pct: Optional[float] = Field(None, ge=0, le=100)
    test_method: Optional[str] = None
    lab_id: Optional[str] = None


class RetailData(EventDataBase):
    price_cents: int = Field(..., ge=0)
    currency: str = "INR"
    quantity_kg: float = Field(..., ge=0)
    store_id: Optional[str] = None
    shelf_life_days: Optional[int] = None
    packaging_type: Optional[str] = None


# Union type for event data
EventData = Union[
    HarvestData,
    ProcessingData,
    LogisticsData,
    PriceData,
    QualityData,
    RetailData
]


class SupplyChainEventBase(BaseModel):
    crop_id: int
    event_type: EventType
    actor_role: str = Field(..., min_length=1, max_length=100)
    actor_id: str = Field(..., min_length=1, max_length=100)
    timestamp: datetime
    location: Optional[str] = Field(None, max_length=500)
    data_json: Dict[str, Any]


class SupplyChainEventCreate(SupplyChainEventBase):
    pass


class SupplyChainEventUpdate(BaseModel):
    status: Optional[EventStatus] = None
    anomaly_score: Optional[int] = Field(None, ge=0, le=100)
    review_id: Optional[int] = None
    anchor_batch_id: Optional[int] = None


class SupplyChainEventResponse(SupplyChainEventBase):
    id: int
    status: EventStatus
    anomaly_score: int
    review_id: Optional[int] = None
    data_hash: Optional[str] = None
    anchor_batch_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Anomaly Flag models
class AnomalyFlagResponse(BaseModel):
    id: int
    event_id: int
    score: int
    features_json: Dict[str, Any]
    threshold: int
    model_version: str
    status: AnomalyStatus
    admin_notes: Optional[str] = None
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


# Review Queue models
class ReviewQueueCreate(BaseModel):
    event_id: int
    anomaly_flag_id: Optional[int] = None
    priority: int = 0
    assigned_to: Optional[str] = None


class ReviewQueueUpdate(BaseModel):
    status: Optional[ReviewStatus] = None
    action: Optional[str] = None
    notes: Optional[str] = None
    assigned_to: Optional[str] = None


class ReviewQueueResponse(BaseModel):
    id: int
    event_id: int
    anomaly_flag_id: Optional[int] = None
    priority: int
    assigned_to: Optional[str] = None
    status: ReviewStatus
    action: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ReviewActionRequest(BaseModel):
    action: str = Field(..., pattern=r"^(accept|reject|needs_more_info)$")
    notes: Optional[str] = None
    admin_id: str = Field(..., min_length=1)


# Blockchain Anchor models
class BlockchainAnchorCreate(BaseModel):
    event_ids: List[int]


class BlockchainAnchorResponse(BaseModel):
    id: int
    batch_hash: str
    merkle_root: str
    event_ids_json: List[int]
    tx_hash: Optional[str] = None
    block_number: Optional[int] = None
    timestamp: datetime
    status: AnchorStatus
    event_count: int
    prev_batch_hash: Optional[str] = None
    error_message: Optional[str] = None

    class Config:
        from_attributes = True


# Verification models
class VerificationResponse(BaseModel):
    event_id: int
    data_hash: str
    is_verified: bool
    anchor_tx_hash: Optional[str] = None
    anchor_block_number: Optional[int] = None
    anchor_timestamp: Optional[datetime] = None
    batch_hash: Optional[str] = None
    merkle_proof: Optional[List[str]] = None


# Traceability models
class TraceEventResponse(BaseModel):
    event_id: int
    event_type: EventType
    actor_role: str
    actor_id: str
    timestamp: datetime
    location: Optional[str] = None
    data_json: Dict[str, Any]
    status: EventStatus
    anomaly_score: int
    is_anomalous: bool
    anchor_tx_hash: Optional[str] = None


class TraceResponse(BaseModel):
    crop_id: int
    batch_code: str
    crop_name: str
    variety: Optional[str] = None
    farm_name: str
    farm_location: str
    events: List[TraceEventResponse]
    latest_anchor: Optional[BlockchainAnchorResponse] = None


# Pagination
class PaginatedResponse(BaseModel):
    items: List[Any]
    total: int
    page: int
    page_size: int
    total_pages: int


# Health check
class HealthResponse(BaseModel):
    status: str
    database: str
    blockchain: str
    timestamp: datetime
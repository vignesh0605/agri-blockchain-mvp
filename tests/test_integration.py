"""Integration tests for full flow"""

import pytest
from datetime import datetime, timedelta
from fastapi.testclient import TestClient

from backend.app import app
from backend.database import SessionLocal, Base, engine
from backend.database import Farm, Crop, SupplyChainEvent, EventType, EventStatus


@pytest.fixture(scope="module")
def client():
    """Create test client"""
    # Create tables
    Base.metadata.create_all(bind=engine)
    yield TestClient(app)
    # Cleanup
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db():
    """Database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def test_create_farm(client):
    """Test farm creation"""
    response = client.post("/farms", json={
        "name": "Test Farm",
        "location": "Test Location",
        "gstin": "27TEST1234F1Z5",
        "wallet_address": "0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266",
        "contact_email": "test@example.com"
    })
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Test Farm"
    assert data["gstin"] == "27TEST1234F1Z5"
    return data["id"]


def test_create_crop(client):
    """Test crop creation"""
    farm_id = test_create_farm(client)

    response = client.post("/crops", json={
        "farm_id": farm_id,
        "name": "Tomato",
        "variety": "Roma",
        "batch_code": "TEST-001",
        "planting_date": "2026-10-01T00:00:00"
    })
    assert response.status_code == 201
    data = response.json()
    assert data["batch_code"] == "TEST-001"
    return data["id"]


def test_create_normal_event(client):
    """Test creating a normal event (should be committed)"""
    crop_id = test_create_crop(client)

    response = client.post("/events", json={
        "crop_id": crop_id,
        "event_type": "harvest",
        "actor_role": "farmer",
        "actor_id": "0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266",
        "timestamp": datetime.utcnow().isoformat(),
        "location": "Test Farm",
        "data_json": {
            "quantity_kg": 1000,
            "grade": "A",
            "moisture_pct": 12
        }
    })
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "committed"
    assert data["anomaly_score"] <= 30
    return data["id"]


def test_create_anomalous_event(client):
    """Test creating an anomalous price event (should be flagged)"""
    crop_id = test_create_crop(client)

    # First create a normal price event
    client.post("/events", json={
        "crop_id": crop_id,
        "event_type": "price",
        "actor_role": "wholesaler",
        "actor_id": "WHOLE-001",
        "timestamp": datetime.utcnow().isoformat(),
        "location": "Market",
        "data_json": {
            "price_cents": 1500,
            "currency": "INR",
            "price_type": "wholesale",
            "quantity_kg": 100,
            "grade": "A"
        }
    })

    # Now create anomalous price (100% increase)
    response = client.post("/events", json={
        "crop_id": crop_id,
        "event_type": "price",
        "actor_role": "retailer",
        "actor_id": "RETAIL-001",
        "timestamp": datetime.utcnow().isoformat(),
        "location": "Market",
        "data_json": {
            "price_cents": 5000,  # 233% increase!
            "currency": "INR",
            "price_type": "retail",
            "quantity_kg": 10,
            "grade": "A"
        }
    })
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "flagged"
    assert data["anomaly_score"] > 30
    return data["id"]


def test_get_pending_reviews(client):
    """Test getting pending reviews"""
    test_create_anomalous_event(client)

    response = client.get("/reviews")
    assert response.status_code == 200
    data = response.json()
    assert len(data) > 0
    assert data[0]["status"] in ["pending", "in_progress"]


def test_review_action_accept(client):
    """Test accepting a review"""
    event_id = test_create_anomalous_event(client)

    # Get review for event
    response = client.get(f"/reviews/event/{event_id}")
    assert response.status_code == 200
    review = response.json()

    # Accept the review
    response = client.post(f"/reviews/{review['id']}/action", json={
        "action": "accept",
        "notes": "Price surge due to demand",
        "admin_id": "admin"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["action"] == "accepted"
    assert data["status"] == "accepted"

    # Verify event is now committed
    from backend.crud import get_event
    db = SessionLocal()
    try:
        event = get_event(db, event_id)
        assert event.status == EventStatus.COMMITTED
    finally:
        db.close()


def test_review_action_reject(client):
    """Test rejecting a review"""
    crop_id = test_create_crop(client)

    # Create another anomalous event
    response = client.post("/events", json={
        "crop_id": crop_id,
        "event_type": "price",
        "actor_role": "retailer",
        "actor_id": "RETAIL-002",
        "timestamp": datetime.utcnow().isoformat(),
        "location": "Market",
        "data_json": {
            "price_cents": 10000,  # Extreme anomaly
            "currency": "INR",
            "price_type": "retail",
            "quantity_kg": 5,
            "grade": "A"
        }
    })
    event_id = response.json()["id"]

    # Get review
    response = client.get(f"/reviews/event/{event_id}")
    review = response.json()

    # Reject the review
    response = client.post(f"/reviews/{review['id']}/action", json={
        "action": "reject",
        "notes": "Data entry error",
        "admin_id": "admin"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["action"] == "rejected"

    # Verify event is rejected
    from backend.crud import get_event
    db = SessionLocal()
    try:
        event = get_event(db, event_id)
        assert event.status == EventStatus.REJECTED
    finally:
        db.close()


def test_traceability(client):
    """Test traceability endpoint"""
    crop_id = test_create_crop(client)

    # Create a few events
    client.post("/events", json={
        "crop_id": crop_id,
        "event_type": "harvest",
        "actor_role": "farmer",
        "actor_id": "FARMER-001",
        "timestamp": datetime.utcnow().isoformat(),
        "location": "Farm",
        "data_json": {"quantity_kg": 500, "grade": "A", "moisture_pct": 11}
    })

    response = client.get(f"/trace/{crop_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["crop_id"] == crop_id
    assert data["batch_code"] == "TEST-001"
    assert len(data["events"]) >= 1


def test_health_check(client):
    """Test health endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ["ok", "degraded"]
    assert "database" in data
    assert "blockchain" in data


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
#!/usr/bin/env python3
"""
Generate sample data for the Agri Supply Chain MVP demo
Creates a realistic farm-to-consumer scenario with normal and anomalous events
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta
import random

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from database import SessionLocal, Farm, Crop, SupplyChainEvent, EventType, EventStatus
from anomaly import analyze_event


def main():
    db = SessionLocal()
    try:
        print("🌱 Generating sample data...")

        # Clear existing data
        db.query(SupplyChainEvent).delete()
        db.query(Crop).delete()
        db.query(Farm).delete()
        db.commit()

        # 1. Create Farm
        farm = Farm(
            name="Green Valley Farms",
            location="Nashik, Maharashtra, India",
            gstin="27ABCDE1234F1Z5",
            wallet_address="0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266",
            contact_email="contact@greenvalley.example",
            contact_phone="+91-9876543210",
            certifications=["Organic", "GAP Certified", "Fair Trade"]
        )
        db.add(farm)
        db.commit()
        db.refresh(farm)
        print(f"✅ Created farm: {farm.name} (ID: {farm.id})")

        # 2. Create Crop
        crop = Crop(
            farm_id=farm.id,
            name="Tomato",
            variety="Roma",
            batch_code="TOM-2026-001",
            planting_date=datetime(2026, 10, 1),
            harvest_window_start=datetime(2026, 12, 20),
            harvest_window_end=datetime(2026, 12, 30),
            expected_yield_kg=1000,
            certifications=["Organic"],
            metadata_json={"field": "A-12", "irrigation": "drip"}
        )
        db.add(crop)
        db.commit()
        db.refresh(crop)
        print(f"✅ Created crop: {crop.name} {crop.variety} (Batch: {crop.batch_code})")

        harvest_date = datetime(2026, 12, 20)

        # 3. Create Events - Normal flow
        events_data = [
            # Harvest event - normal
            {
                "crop_id": crop.id,
                "event_type": EventType.HARVEST,
                "actor_role": "farmer",
                "actor_id": farm.wallet_address,
                "timestamp": harvest_date,
                "location": "Green Valley Farms, Field A-12",
                "data_json": {
                    "quantity_kg": 950,
                    "grade": "A",
                    "moisture_pct": 11.5,
                    "harvest_method": "manual",
                    "field_id": "A-12"
                }
            },
            # Processing event - normal
            {
                "crop_id": crop.id,
                "event_type": EventType.PROCESSING,
                "actor_role": "processor",
                "actor_id": "PROC-001",
                "timestamp": harvest_date + timedelta(days=1),
                "location": "FreshPack Processing Unit, Nashik",
                "data_json": {
                    "input_quantity_kg": 950,
                    "output_quantity_kg": 920,
                    "processing_type": "washing_sorting_packaging",
                    "grade_in": "A",
                    "grade_out": "A",
                    "facility_id": "FP-NASHIK-01",
                    "batch_ids_in": ["TOM-2026-001"]
                }
            },
            # Logistics event - normal
            {
                "crop_id": crop.id,
                "event_type": EventType.LOGISTICS,
                "actor_role": "transporter",
                "actor_id": "TRANS-001",
                "timestamp": harvest_date + timedelta(days=2),
                "location": "Nashik → Mumbai Cold Chain",
                "data_json": {
                    "quantity_kg": 920,
                    "transport_mode": "truck",
                    "temperature_c": 4.0,
                    "humidity_pct": 85,
                    "distance_km": 180,
                    "vehicle_id": "MH-12-AB-1234",
                    "driver_id": "DRV-001",
                    "origin": "Nashik",
                    "destination": "Mumbai APMC"
                }
            },
            # Quality check - normal
            {
                "crop_id": crop.id,
                "event_type": EventType.QUALITY,
                "actor_role": "quality_inspector",
                "actor_id": "QC-001",
                "timestamp": harvest_date + timedelta(days=3),
                "location": "Mumbai APMC Quality Lab",
                "data_json": {
                    "grade": "A",
                    "moisture_pct": 11.8,
                    "size_mm": 55,
                    "color_score": 9,
                    "firmness": 8,
                    "defects_pct": 2,
                    "test_method": "visual_chemical",
                    "lab_id": "APMC-LAB-01"
                }
            },
            # Wholesale price - normal market price
            {
                "crop_id": crop.id,
                "event_type": EventType.PRICE,
                "actor_role": "wholesaler",
                "actor_id": "WHOLE-001",
                "timestamp": harvest_date + timedelta(days=3, hours=2),
                "location": "Mumbai APMC Market",
                "data_json": {
                    "price_cents": 1500,  # ₹15/kg
                    "currency": "INR",
                    "price_type": "wholesale",
                    "quantity_kg": 920,
                    "market_id": "MUMBAI-APMC",
                    "grade": "A"
                }
            },
            # Retail price - normal
            {
                "crop_id": crop.id,
                "event_type": EventType.RETAIL,
                "actor_role": "retailer",
                "actor_id": "RETAIL-001",
                "timestamp": harvest_date + timedelta(days=5),
                "location": "FreshMart Supermarket, Mumbai",
                "data_json": {
                    "price_cents": 2500,  # ₹25/kg
                    "currency": "INR",
                    "quantity_kg": 20,
                    "store_id": "FM-MUM-001",
                    "shelf_life_days": 7,
                    "packaging_type": "clamshell_500g"
                }
            }
        ]

        # Create events with anomaly detection
        all_events = []
        for i, event_data in enumerate(events_data):
            # Get history for anomaly detection
            history = [{
                "id": e.id,
                "crop_id": e.crop_id,
                "event_type": e.event_type.value,
                "actor_role": e.actor_role,
                "actor_id": e.actor_id,
                "timestamp": e.timestamp.timestamp(),
                "location": e.location,
                "data_json": e.data_json
            } for e in all_events]

            # Add harvest_date to event for lead time calculation
            event_data["harvest_date"] = harvest_date.timestamp()

            # Analyze for anomalies
            anomaly_score, features = analyze_event(event_data, history)
            event_data["anomaly_score"] = anomaly_score

            # Determine status based on anomaly score
            if anomaly_score > 70:
                event_data["status"] = EventStatus.FLAGGED
            elif anomaly_score > 30:
                event_data["status"] = EventStatus.FLAGGED
            else:
                event_data["status"] = EventStatus.COMMITTED

            event = SupplyChainEvent(**event_data)
            db.add(event)
            db.commit()
            db.refresh(event)
            all_events.append(event)

            status_emoji = "🟢" if event.status == EventStatus.COMMITTED else "🟡"
            print(f"  {status_emoji} Event #{event.id}: {event.event_type.value} - Score: {anomaly_score} - Status: {event.status.value}")

        # 4. Add ANOMALOUS event - Retail price spike
        print("\n⚠️  Adding ANOMALOUS event (price spike)...")
        anomalous_event = {
            "crop_id": crop.id,
            "event_type": EventType.PRICE,
            "actor_role": "retailer",
            "actor_id": "RETAIL-002",
            "timestamp": harvest_date + timedelta(days=7),
            "location": "Premium Grocers, Mumbai",
            "data_json": {
                "price_cents": 5000,  # ₹50/kg - 100% increase from wholesale!
                "currency": "INR",
                "price_type": "retail",
                "quantity_kg": 10,
                "market_id": "PREMIUM-GROCERS",
                "grade": "A"
            },
            "harvest_date": harvest_date.timestamp()
        }

        history = [{
            "id": e.id,
            "crop_id": e.crop_id,
            "event_type": e.event_type.value,
            "actor_role": e.actor_role,
            "actor_id": e.actor_id,
            "timestamp": e.timestamp.timestamp(),
            "location": e.location,
            "data_json": e.data_json
        } for e in all_events]

        anomaly_score, features = analyze_event(anomalous_event, history)
        anomalous_event["anomaly_score"] = anomaly_score
        anomalous_event["status"] = EventStatus.FLAGGED

        event = SupplyChainEvent(**anomalous_event)
        db.add(event)
        db.commit()
        db.refresh(event)
        all_events.append(event)

        print(f"  🔴 Event #{event.id}: {event.event_type.value} - Score: {anomaly_score} - Status: {event.status.value}")
        print(f"     Features: {features}")

        # Summary
        print(f"\n📊 Summary:")
        print(f"   Farm: {farm.name}")
        print(f"   Crop: {crop.batch_code} - {crop.name} {crop.variety}")
        print(f"   Total Events: {len(all_events)}")
        committed = sum(1 for e in all_events if e.status == EventStatus.COMMITTED)
        flagged = sum(1 for e in all_events if e.status == EventStatus.FLAGGED)
        print(f"   Committed: {committed}")
        print(f"   Flagged for Review: {flagged}")

        print("\n✅ Sample data generated successfully!")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    main()
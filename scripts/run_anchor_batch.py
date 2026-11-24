#!/usr/bin/env python3
"""
CLI script to run batch anchoring to blockchain
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from anchor_service import get_anchor_service
from database import SessionLocal, BlockchainAnchor, AnchorStatus


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Anchor committed events to blockchain")
    parser.add_argument("--max-events", type=int, default=10, help="Max events per batch")
    parser.add_argument("--anchor-id", type=int, help="Submit existing anchor by ID")
    parser.add_argument("--list", action="store_true", help="List all anchors")
    parser.add_argument("--verify", type=int, help="Verify event by ID")
    args = parser.parse_args()

    service = get_anchor_service()

    if args.list:
        db = SessionLocal()
        try:
            anchors = db.query(BlockchainAnchor).order_by(BlockchainAnchor.id.desc()).all()
            if not anchors:
                print("No anchors found")
                return
            print(f"{'ID':<5} {'Batch Hash':<20} {'Events':<7} {'Status':<12} {'Tx Hash':<20} {'Block'}")
            print("-" * 100)
            for a in anchors:
                tx_short = a.tx_hash[:18] + "..." if a.tx_hash else "N/A"
                print(f"{a.id:<5} {a.batch_hash[:18]}... {a.event_count:<7} {a.status.value:<12} {tx_short:<20} {a.block_number or 'N/A'}")
        finally:
            db.close()
        return

    if args.verify:
        result = service.verify_event(args.verify)
        if result.get("verified"):
            print(f"✅ Event #{args.verify} VERIFIED")
            print(f"   Data Hash: {result.get('data_hash')}")
            print(f"   Anchor TX: {result.get('anchor_tx_hash')}")
            print(f"   Block: {result.get('anchor_block_number')}")
            print(f"   Batch Hash: {result.get('batch_hash')}")
            print(f"   Merkle Root: {result.get('merkle_root')}")
        else:
            print(f"❌ Event #{args.verify} NOT VERIFIED: {result.get('error')}")
        return

    if args.anchor_id:
        print(f"Submitting anchor #{args.anchor_id}...")
        success = service.submit_batch(args.anchor_id)
        if success:
            print("✅ Anchor submitted successfully")
        else:
            print("❌ Failed to submit anchor")
            sys.exit(1)
        return

    # Create and submit new batch
    print(f"Creating batch with max {args.max_events} events...")
    anchor = service.anchor_batch(max_events=args.max_events)
    if anchor:
        print(f"✅ Batch anchored successfully!")
        print(f"   Anchor ID: {anchor.id}")
        print(f"   Batch Hash: {anchor.batch_hash}")
        print(f"   Merkle Root: {anchor.merkle_root}")
        print(f"   Events: {anchor.event_count}")
        print(f"   TX Hash: {anchor.tx_hash}")
        print(f"   Block: {anchor.block_number}")
    else:
        print("❌ No events to anchor or anchoring failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
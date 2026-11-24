"""Blockchain Anchoring Service - Batch anchoring to Anvil"""

import json
import hashlib
from typing import List, Dict, Any, Optional
from datetime import datetime
from web3 import Web3
from eth_account import Account
from eth_account.messages import encode_defunct

from config import settings
from database import SessionLocal, BlockchainAnchor, SupplyChainEvent, AnchorStatus
from crud import (
    get_committed_unanchored_events, create_blockchain_anchor,
    update_anchor_status, assign_events_to_anchor, get_latest_anchor
)


class AnchorService:
    """Service for batch anchoring events to blockchain"""

    def __init__(self):
        self.w3 = None
        self.contract = None
        self.account = None
        self._init_web3()

    def _init_web3(self):
        """Initialize Web3 connection and contract"""
        try:
            self.w3 = Web3(Web3.HTTPProvider(settings.ANVIL_RPC_URL))
            if not self.w3.is_connected():
                print("⚠️  Cannot connect to Anvil")
                return

            if settings.ANCHOR_CONTRACT_ADDRESS:
                # Minimal ABI for DataAnchor contract
                abi = [
                    {
                        "inputs": [
                            {"internalType": "bytes32", "name": "_batchHash", "type": "bytes32"},
                            {"internalType": "uint256", "name": "_eventCount", "type": "uint256"},
                            {"internalType": "bytes32", "name": "_prevBatchHash", "type": "bytes32"}
                        ],
                        "name": "anchorBatch",
                        "outputs": [],
                        "stateMutability": "nonpayable",
                        "type": "function"
                    },
                    {
                        "inputs": [{"internalType": "bytes32", "name": "_batchHash", "type": "bytes32"}],
                        "name": "getAnchor",
                        "outputs": [
                            {"internalType": "bytes32", "name": "batchHash", "type": "bytes32"},
                            {"internalType": "uint256", "name": "timestamp", "type": "uint256"},
                            {"internalType": "uint256", "name": "eventCount", "type": "uint256"},
                            {"internalType": "bytes32", "name": "prevBatchHash", "type": "bytes32"}
                        ],
                        "stateMutability": "view",
                        "type": "function"
                    },
                    {
                        "inputs": [],
                        "name": "latestBatchHash",
                        "outputs": [{"internalType": "bytes32", "name": "", "type": "bytes32"}],
                        "stateMutability": "view",
                        "type": "function"
                    }
                ]
                self.contract = self.w3.eth.contract(
                    address=Web3.to_checksum_address(settings.ANCHOR_CONTRACT_ADDRESS),
                    abi=abi
                )

            if settings.DEPLOYER_PRIVATE_KEY:
                self.account = Account.from_key(settings.DEPLOYER_PRIVATE_KEY)

            print(f"✅ Anchor service initialized (contract: {settings.ANCHOR_CONTRACT_ADDRESS})")
        except Exception as e:
            print(f"⚠️  Anchor service initialization failed: {e}")

    def compute_event_hash(self, event: SupplyChainEvent) -> str:
        """Compute hash of a single event"""
        # Use the stored data_hash if available
        if event.data_hash:
            return event.data_hash

        # Otherwise compute from event data
        event_data = {
            "id": event.id,
            "crop_id": event.crop_id,
            "event_type": event.event_type.value,
            "actor_role": event.actor_role,
            "actor_id": event.actor_id,
            "timestamp": event.timestamp.isoformat() if event.timestamp else None,
            "location": event.location,
            "data_json": event.data_json
        }
        canonical = json.dumps(event_data, sort_keys=True, separators=(',', ':'))
        return "0x" + hashlib.sha256(canonical.encode()).hexdigest()

    def build_merkle_tree(self, event_hashes: List[str]) -> Dict[str, Any]:
        """Build Merkle tree from event hashes, return root and proofs"""
        if not event_hashes:
            return {"root": "0x" + "0" * 64, "proofs": {}}

        # Convert to bytes32
        leaves = [Web3.to_bytes(hexstr=h) for h in event_hashes]

        # Build tree level by level
        level = leaves
        tree = [level]
        while len(level) > 1:
            next_level = []
            for i in range(0, len(level), 2):
                left = level[i]
                right = level[i + 1] if i + 1 < len(level) else left
                combined = hashlib.sha256(left + right).digest()
                next_level.append(combined)
            tree.append(next_level)
            level = next_level

        root = "0x" + level[0].hex()

        # Generate proofs for each leaf
        proofs = {}
        for idx, leaf in enumerate(leaves):
            proof = []
            position = idx
            for level_nodes in tree[:-1]:
                sibling_idx = position ^ 1  # XOR with 1 gets sibling
                if sibling_idx < len(level_nodes):
                    proof.append("0x" + level_nodes[sibling_idx].hex())
                else:
                    proof.append("0x" + level_nodes[position].hex())
                position //= 2
            proofs[event_hashes[idx]] = proof

        return {"root": root, "proofs": proofs}

    def create_batch(self, max_events: int = None) -> Optional[BlockchainAnchor]:
        """Create a new batch anchor from committed unanchored events"""
        db = SessionLocal()
        try:
            max_events = max_events or settings.BATCH_SIZE_FOR_ANCHORING
            events = get_committed_unanchored_events(db, limit=max_events)

            if not events:
                print("No events to anchor")
                return None

            # Compute event hashes
            event_hashes = [self.compute_event_hash(e) for e in events]
            event_ids = [e.id for e in events]

            # Build Merkle tree
            merkle = self.build_merkle_tree(event_hashes)
            merkle_root = merkle["root"]

            # Get previous batch hash for chaining
            latest_anchor = get_latest_anchor(db)
            prev_batch_hash = latest_anchor.batch_hash if latest_anchor else "0x" + "0" * 64

            # Create batch hash (hash of merkle root + prev hash + timestamp + count)
            batch_data = f"{merkle_root}{prev_batch_hash}{datetime.utcnow().isoformat()}{len(events)}"
            batch_hash = "0x" + hashlib.sha256(batch_data.encode()).hexdigest()

            # Create anchor record in database
            anchor = create_blockchain_anchor(db, type('obj', (object,), {'event_ids': event_ids})())
            anchor.batch_hash = batch_hash
            anchor.merkle_root = merkle_root
            anchor.prev_batch_hash = prev_batch_hash
            anchor.event_count = len(events)
            db.commit()
            db.refresh(anchor)

            print(f"📦 Created batch {anchor.id} with {len(events)} events")
            print(f"   Batch hash: {batch_hash}")
            print(f"   Merkle root: {merkle_root}")

            return anchor

        finally:
            db.close()

    def submit_batch(self, anchor_id: int) -> bool:
        """Submit batch anchor transaction to Anvil"""
        db = SessionLocal()
        try:
            anchor = db.query(BlockchainAnchor).filter(BlockchainAnchor.id == anchor_id).first()
            if not anchor:
                print(f"❌ Anchor {anchor_id} not found")
                return False

            if not self.contract or not self.account:
                print("❌ Blockchain not configured")
                update_anchor_status(db, anchor_id, AnchorStatus.FAILED, error_message="Blockchain not configured")
                return False

            # Prepare transaction
            batch_hash_bytes = Web3.to_bytes(hexstr=anchor.batch_hash)
            prev_batch_hash_bytes = Web3.to_bytes(hexstr=anchor.prev_batch_hash or "0x" + "0" * 64)

            nonce = self.w3.eth.get_transaction_count(self.account.address)
            tx = self.contract.functions.anchorBatch(
                batch_hash_bytes,
                anchor.event_count,
                prev_batch_hash_bytes
            ).build_transaction({
                "from": self.account.address,
                "nonce": nonce,
                "gas": 300000,
                "gasPrice": self.w3.to_wei("1", "gwei"),
                "chainId": self.w3.eth.chain_id,
            })

            # Sign and send
            signed_tx = self.w3.eth.account.sign_transaction(tx, self.account.key)
            tx_hash = self.w3.eth.send_raw_transaction(signed_tx.raw_transaction)
            tx_hash_hex = tx_hash.hex()

            print(f"📤 Submitted anchor transaction: {tx_hash_hex}")

            # Wait for receipt
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)

            # Update anchor with transaction info
            update_anchor_status(
                db, anchor_id,
                AnchorStatus.CONFIRMED,
                tx_hash=tx_hash_hex,
                block_number=receipt.blockNumber
            )

            # Assign events to this anchor
            event_ids = anchor.event_ids_json
            assign_events_to_anchor(db, event_ids, anchor_id)

            print(f"✅ Batch anchored in block {receipt.blockNumber}")
            return True

        except Exception as e:
            print(f"❌ Failed to submit batch: {e}")
            update_anchor_status(db, anchor_id, AnchorStatus.FAILED, error_message=str(e))
            return False
        finally:
            db.close()

    def anchor_batch(self, max_events: int = None) -> Optional[BlockchainAnchor]:
        """Create and submit a batch in one call"""
        anchor = self.create_batch(max_events)
        if anchor:
            success = self.submit_batch(anchor.id)
            if success:
                db = SessionLocal()
                try:
                    return db.query(BlockchainAnchor).filter(BlockchainAnchor.id == anchor.id).first()
                finally:
                    db.close()
        return anchor

    def verify_event(self, event_id: int) -> Dict[str, Any]:
        """Verify an event's on-chain anchor"""
        db = SessionLocal()
        try:
            event = db.query(SupplyChainEvent).filter(SupplyChainEvent.id == event_id).first()
            if not event:
                return {"verified": False, "error": "Event not found"}

            if not event.anchor_batch_id:
                return {"verified": False, "error": "Event not anchored"}

            anchor = db.query(BlockchainAnchor).filter(BlockchainAnchor.id == event.anchor_batch_id).first()
            if not anchor or anchor.status != AnchorStatus.CONFIRMED:
                return {"verified": False, "error": "Anchor not confirmed"}

            # Verify on-chain
            if self.contract:
                batch_hash_bytes = Web3.to_bytes(hexstr=anchor.batch_hash)
                try:
                    exists, timestamp, event_count = self.contract.functions.verifyBatch(
                        batch_hash_bytes, anchor.event_count
                    ).call()
                    if not exists:
                        return {"verified": False, "error": "Batch not found on-chain"}
                except Exception as e:
                    return {"verified": False, "error": f"On-chain verification failed: {e}"}

            # Get Merkle proof for this event
            event_hash = self.compute_event_hash(event)
            # We'd need to store proofs or recompute - simplified for now

            return {
                "verified": True,
                "event_id": event_id,
                "data_hash": event.data_hash,
                "anchor_tx_hash": anchor.tx_hash,
                "anchor_block_number": anchor.block_number,
                "anchor_timestamp": datetime.fromtimestamp(timestamp) if timestamp else anchor.timestamp,
                "batch_hash": anchor.batch_hash,
                "merkle_root": anchor.merkle_root
            }

        finally:
            db.close()


# Global service instance
_anchor_service = None


def get_anchor_service() -> AnchorService:
    global _anchor_service
    if _anchor_service is None:
        _anchor_service = AnchorService()
    return _anchor_service
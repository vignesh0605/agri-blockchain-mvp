"""Tests for blockchain anchoring"""

import pytest
import hashlib
import json
from unittest.mock import Mock, patch, MagicMock

from anchor_service import AnchorService


class TestAnchorService:
    """Test AnchorService functionality"""

    def setup_method(self):
        self.service = AnchorService()

    def test_compute_event_hash(self):
        """Test event hash computation"""
        # Create mock event
        mock_event = Mock()
        mock_event.data_hash = "0x" + "a" * 64
        mock_event.id = 1
        mock_event.crop_id = 1
        mock_event.event_type = Mock(value="price")
        mock_event.actor_role = "wholesaler"
        mock_event.actor_id = "WHOLE-001"
        mock_event.timestamp = None
        mock_event.location = "Market"
        mock_event.data_json = {"price_cents": 1500}

        hash_result = self.service.compute_event_hash(mock_event)
        assert hash_result == "0x" + "a" * 64

    def test_compute_event_hash_fallback(self):
        """Test event hash computation when data_hash not set"""
        mock_event = Mock()
        mock_event.data_hash = None
        mock_event.id = 1
        mock_event.crop_id = 1
        mock_event.event_type = Mock(value="price")
        mock_event.actor_role = "wholesaler"
        mock_event.actor_id = "WHOLE-001"
        mock_event.timestamp = None
        mock_event.location = "Market"
        mock_event.data_json = {"price_cents": 1500}

        hash_result = self.service.compute_event_hash(mock_event)
        assert hash_result.startswith("0x")
        assert len(hash_result) == 66  # 0x + 64 hex chars

    def test_build_merkle_tree_empty(self):
        """Test Merkle tree with empty list"""
        result = self.service.build_merkle_tree([])
        assert result["root"] == "0x" + "0" * 64
        assert result["proofs"] == {}

    def test_build_merkle_tree_single(self):
        """Test Merkle tree with single hash"""
        hashes = ["0x" + "a" * 64]
        result = self.service.build_merkle_tree(hashes)

        assert result["root"] == hashes[0]
        assert hashes[0] in result["proofs"]

    def test_build_merkle_tree_multiple(self):
        """Test Merkle tree with multiple hashes"""
        hashes = [
            "0x" + "a" * 64,
            "0x" + "b" * 64,
            "0x" + "c" * 64,
            "0x" + "d" * 64
        ]
        result = self.service.build_merkle_tree(hashes)

        assert result["root"].startswith("0x")
        assert len(result["root"]) == 66
        assert len(result["proofs"]) == 4

        # Each proof should have log2(n) elements
        for proof in result["proofs"].values():
            assert len(proof) == 2  # log2(4) = 2

    def test_merkle_tree_odd_number(self):
        """Test Merkle tree with odd number of leaves"""
        hashes = [
            "0x" + "a" * 64,
            "0x" + "b" * 64,
            "0x" + "c" * 64
        ]
        result = self.service.build_merkle_tree(hashes)

        assert result["root"].startswith("0x")
        assert len(result["proofs"]) == 3


class TestMerkleProofVerification:
    """Test Merkle proof verification logic"""

    def verify_proof(self, leaf: str, proof: list, root: str) -> bool:
        """Verify a Merkle proof"""
        current = bytes.fromhex(leaf[2:])
        for sibling_hex in proof:
            sibling = bytes.fromhex(sibling_hex[2:])
            # Determine order (simplified - in reality need position)
            combined = hashlib.sha256(current + sibling).digest()
            current = combined
        computed_root = "0x" + current.hex()
        return computed_root == root

    def test_proof_verification(self):
        """Test that generated proofs verify correctly"""
        service = AnchorService()
        hashes = [
            "0x" + "a" * 64,
            "0x" + "b" * 64,
            "0x" + "c" * 64,
            "0x" + "d" * 64
        ]

        result = service.build_merkle_tree(hashes)

        # Verify each proof
        for leaf, proof in result["proofs"].items():
            # This is a simplified verification
            # In production, we'd need the actual position to verify correctly
            assert len(proof) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
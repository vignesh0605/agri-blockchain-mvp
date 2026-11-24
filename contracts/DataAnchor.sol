// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/**
 * @title DataAnchor
 * @dev Minimal smart contract for anchoring batch hashes to blockchain
 * Only stores cryptographic hashes - no business logic on-chain
 */
contract DataAnchor {
    // Single mapping: batch hash → anchor record
    struct AnchorRecord {
        bytes32 batchHash;      // Merkle root of batch
        uint256 timestamp;      // When anchored
        uint256 eventCount;     // Number of events in batch
        bytes32 prevBatchHash;  // Chain to previous batch (optional)
    }

    bytes32 public latestBatchHash;
    AnchorRecord[] public anchors;
    mapping(bytes32 => uint256) public anchorIndex; // batchHash → index

    event Anchored(
        bytes32 indexed batchHash,
        uint256 timestamp,
        uint256 eventCount,
        bytes32 prevBatchHash
    );

    constructor() {}

    /**
     * @dev Anchor a new batch of events
     * @param _batchHash Merkle root of the batch
     * @param _eventCount Number of events in this batch
     * @param _prevBatchHash Previous batch hash for chaining (optional)
     */
    function anchorBatch(
        bytes32 _batchHash,
        uint256 _eventCount,
        bytes32 _prevBatchHash
    ) external {
        uint256 index = anchors.length;
        anchors.push(AnchorRecord({
            batchHash: _batchHash,
            timestamp: block.timestamp,
            eventCount: _eventCount,
            prevBatchHash: _prevBatchHash
        }));
        anchorIndex[_batchHash] = index;
        latestBatchHash = _batchHash;

        emit Anchored(_batchHash, block.timestamp, _eventCount, _prevBatchHash);
    }

    /**
     * @dev Get anchor record by batch hash
     * @param _batchHash The batch hash to look up
     * @return AnchorRecord with timestamp, eventCount, prevBatchHash
     */
    function getAnchor(bytes32 _batchHash) external view returns (AnchorRecord memory) {
        uint256 index = anchorIndex[_batchHash];
        require(index < anchors.length, "Anchor not found");
        return anchors[index];
    }

    /**
     * @dev Verify a batch hash exists on-chain with expected event count
     * @param _batchHash The batch hash to verify
     * @param _expectedCount Expected number of events in batch
     * @return (exists, timestamp, eventCount)
     */
    function verifyBatch(bytes32 _batchHash, uint256 _expectedCount)
        external view returns (bool, uint256, uint256)
    {
        uint256 index = anchorIndex[_batchHash];
        if (index >= anchors.length) return (false, 0, 0);
        AnchorRecord memory a = anchors[index];
        return (a.batchHash == _batchHash && a.eventCount == _expectedCount, a.timestamp, a.eventCount);
    }

    /**
     * @dev Get total number of anchored batches
     * @return count of anchors
     */
    function getAnchorCount() external view returns (uint256) {
        return anchors.length;
    }

    /**
     * @dev Get anchor by index
     * @param index Index of the anchor
     * @return AnchorRecord
     */
    function getAnchorByIndex(uint256 index) external view returns (AnchorRecord memory) {
        require(index < anchors.length, "Index out of bounds");
        return anchors[index];
    }
}
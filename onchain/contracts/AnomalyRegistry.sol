// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {AuthorityRegistry} from "./AuthorityRegistry.sol";

/// @title AnomalyRegistry
/// @notice Immutable, publicly-verifiable on-chain record of anomalies
///         detected by the off-chain Transformer Autoencoder + PoA
///         pipeline. Only addresses registered in AuthorityRegistry may
///         submit records. Each record carries `offChainBlockHash`, the
///         SHA-256 hash of the corresponding block in the project's local
///         PoA ledger, linking the two blockchain layers.
contract AnomalyRegistry {
    struct AnomalyRecord {
        uint256 id;
        string meterId;
        string attackType;
        uint16 confidenceBps; // detection confidence, basis points (0-10000 = 0-100%)
        bytes32 offChainBlockHash;
        uint256 timestamp;
        address reportedBy;
    }

    AuthorityRegistry public immutable authorityRegistry;

    AnomalyRecord[] private _records;
    mapping(bytes32 => bool) public offChainHashRecorded;

    event AnomalyRecorded(
        uint256 indexed id,
        string meterId,
        string attackType,
        uint16 confidenceBps,
        bytes32 indexed offChainBlockHash,
        address indexed reportedBy
    );

    modifier onlyAuthority() {
        require(authorityRegistry.isAuthority(msg.sender), "AnomalyRegistry: caller is not an authority");
        _;
    }

    constructor(address authorityRegistryAddress) {
        require(authorityRegistryAddress != address(0), "AnomalyRegistry: zero registry");
        authorityRegistry = AuthorityRegistry(authorityRegistryAddress);
    }

    function recordAnomaly(
        string calldata meterId,
        string calldata attackType,
        uint16 confidenceBps,
        bytes32 offChainBlockHash
    ) external onlyAuthority returns (uint256 id) {
        require(confidenceBps <= 10000, "AnomalyRegistry: confidence out of range");
        require(!offChainHashRecorded[offChainBlockHash], "AnomalyRegistry: duplicate off-chain hash");

        id = _records.length;
        _records.push(
            AnomalyRecord({
                id: id,
                meterId: meterId,
                attackType: attackType,
                confidenceBps: confidenceBps,
                offChainBlockHash: offChainBlockHash,
                timestamp: block.timestamp,
                reportedBy: msg.sender
            })
        );
        offChainHashRecorded[offChainBlockHash] = true;

        emit AnomalyRecorded(id, meterId, attackType, confidenceBps, offChainBlockHash, msg.sender);
    }

    function getRecord(uint256 id) external view returns (AnomalyRecord memory) {
        require(id < _records.length, "AnomalyRegistry: unknown id");
        return _records[id];
    }

    function recordCount() external view returns (uint256) {
        return _records.length;
    }

    /// @notice Paginated read to avoid unbounded return arrays as the
    ///         registry grows over the platform's lifetime.
    function getRecords(uint256 offset, uint256 limit) external view returns (AnomalyRecord[] memory page) {
        uint256 total = _records.length;
        if (offset >= total) {
            return new AnomalyRecord[](0);
        }
        uint256 end = offset + limit;
        if (end > total) {
            end = total;
        }
        page = new AnomalyRecord[](end - offset);
        for (uint256 i = offset; i < end; i++) {
            page[i - offset] = _records[i];
        }
    }
}

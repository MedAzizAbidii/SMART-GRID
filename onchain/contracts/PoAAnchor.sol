// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {AuthorityRegistry} from "./AuthorityRegistry.sol";

/// @title PoAAnchor
/// @notice Periodically anchors the latest block hash of the project's
///         off-chain local Proof-of-Authority ledger onto a public
///         Ethereum network. This gives the local PoA chain public,
///         tamper-evident timestamping without paying gas to store full
///         grid telemetry on-chain — only the hash (and index) of each
///         batch is anchored. Anyone can later prove a given off-chain
///         block existed at or before a given time by matching its hash
///         against `anchors[index]`.
contract PoAAnchor {
    struct Anchor {
        uint256 poaBlockIndex;
        bytes32 poaBlockHash;
        uint256 anchoredAt;
        address anchoredBy;
    }

    AuthorityRegistry public immutable authorityRegistry;

    mapping(uint256 => Anchor) public anchors;
    uint256 public lastAnchoredIndex;
    uint256 public anchorCount;

    event BlockAnchored(uint256 indexed poaBlockIndex, bytes32 indexed poaBlockHash, address indexed anchoredBy);

    modifier onlyAuthority() {
        require(authorityRegistry.isAuthority(msg.sender), "PoAAnchor: caller is not an authority");
        _;
    }

    constructor(address authorityRegistryAddress) {
        require(authorityRegistryAddress != address(0), "PoAAnchor: zero registry");
        authorityRegistry = AuthorityRegistry(authorityRegistryAddress);
    }

    /// @param poaBlockIndex Strictly increasing index from the off-chain
    ///        PoA ledger (chain length at time of anchoring). Prevents
    ///        anchoring stale or reordered blocks.
    function anchorBlock(uint256 poaBlockIndex, bytes32 poaBlockHash) external onlyAuthority {
        require(poaBlockHash != bytes32(0), "PoAAnchor: empty hash");
        require(anchorCount == 0 || poaBlockIndex > lastAnchoredIndex, "PoAAnchor: index not increasing");

        anchors[poaBlockIndex] = Anchor({
            poaBlockIndex: poaBlockIndex,
            poaBlockHash: poaBlockHash,
            anchoredAt: block.timestamp,
            anchoredBy: msg.sender
        });
        lastAnchoredIndex = poaBlockIndex;
        anchorCount += 1;

        emit BlockAnchored(poaBlockIndex, poaBlockHash, msg.sender);
    }

    function verifyAnchor(uint256 poaBlockIndex, bytes32 candidateHash) external view returns (bool) {
        return anchors[poaBlockIndex].poaBlockHash == candidateHash && anchors[poaBlockIndex].poaBlockHash != bytes32(0);
    }
}

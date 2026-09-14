// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/// @title AuthorityRegistry
/// @notice On-chain mirror of the project's off-chain PoA authority set
///         (Utility Operator, Grid Supervisor, Security Auditor, Data
///         Custodian). Only registered authorities may write to
///         AnomalyRegistry or PoAAnchor. The registry owner (deployer,
///         representing grid operations governance) manages membership.
contract AuthorityRegistry {
    address public owner;

    mapping(address => bool) public isAuthority;
    mapping(address => string) public label;
    address[] private _authorityList;

    event AuthorityAdded(address indexed account, string label);
    event AuthorityRemoved(address indexed account);
    event OwnershipTransferred(address indexed previousOwner, address indexed newOwner);

    modifier onlyOwner() {
        require(msg.sender == owner, "AuthorityRegistry: caller is not owner");
        _;
    }

    constructor(address initialOwner) {
        require(initialOwner != address(0), "AuthorityRegistry: zero owner");
        owner = initialOwner;
        emit OwnershipTransferred(address(0), initialOwner);
    }

    function addAuthority(address account, string calldata accountLabel) external onlyOwner {
        require(account != address(0), "AuthorityRegistry: zero address");
        require(!isAuthority[account], "AuthorityRegistry: already registered");
        isAuthority[account] = true;
        label[account] = accountLabel;
        _authorityList.push(account);
        emit AuthorityAdded(account, accountLabel);
    }

    function removeAuthority(address account) external onlyOwner {
        require(isAuthority[account], "AuthorityRegistry: not registered");
        isAuthority[account] = false;
        emit AuthorityRemoved(account);
    }

    function transferOwnership(address newOwner) external onlyOwner {
        require(newOwner != address(0), "AuthorityRegistry: zero owner");
        emit OwnershipTransferred(owner, newOwner);
        owner = newOwner;
    }

    /// @notice Full list of addresses ever registered (including removed
    ///         ones — check `isAuthority` for current membership).
    function authorityList() external view returns (address[] memory) {
        return _authorityList;
    }

    function authorityCount() external view returns (uint256) {
        return _authorityList.length;
    }
}

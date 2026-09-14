"""production/blockchain/onchain_bridge.py

Optional real-blockchain layer: anchors the local PoA ledger
(`blockchain/poa_ledger.py`) onto a public Ethereum network (Sepolia by
default) via the Solidity contracts in `onchain/contracts/`. Fully
additive and OFF by default (`SGRID_ONCHAIN_ENABLED=0`) — nothing here
changes local PoA behavior; api_server.py works identically with the
bridge disabled, the same pattern already used for
`inference_service_url` and `SMARTGRID_AUTO_RECAL`.

Architecture:
  - AuthorityRegistry.sol mirrors the 4 off-chain PoA authorities.
  - PoAAnchor.sol stores (index -> off-chain block_hash) so anyone can
    verify a given local PoA block existed at or before a given on-chain
    timestamp, without paying gas to store full grid telemetry on-chain.
  - AnomalyRegistry.sol records individual high-confidence anomalies
    directly, each tagged with the off-chain PoA block_hash it came from
    — the link between the two blockchain layers.

The bridge is synchronous (web3.py has no native asyncio API); async
callers (api_server.py) run it via `asyncio.to_thread(...)`, the same
pattern already used for the ML detector (see `_ingest_locked`).
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger("smartgrid.onchain")

_web3_import_error: Exception | None = None
try:
    from web3 import Web3
except Exception as exc:  # pragma: no cover - import guard, web3 is an optional dep
    Web3 = None  # type: ignore[assignment]
    _web3_import_error = exc


CONTRACT_NAMES = ["AuthorityRegistry", "AnomalyRegistry", "PoAAnchor"]


class OnchainBridgeUnavailable(RuntimeError):
    """Raised internally when the bridge can't be constructed. Callers
    outside this module never see this — `get_onchain_bridge()` catches it
    and returns None instead, so a missing/misconfigured on-chain layer
    degrades gracefully rather than breaking detection."""


class OnchainBridge:
    """Thin synchronous wrapper around the 3 deployed Solidity contracts.

    Construct via `get_onchain_bridge()`, not directly.
    """

    def __init__(self, onchain_dir: Path, network: str, rpc_url: str, private_key: str) -> None:
        if Web3 is None:
            raise OnchainBridgeUnavailable(f"web3.py not installed: {_web3_import_error}")

        deployment_path = onchain_dir / "deployments" / f"{network}.json"
        if not deployment_path.exists():
            raise OnchainBridgeUnavailable(
                f"No deployment found for network '{network}' at {deployment_path}. "
                f"Run `npx hardhat run scripts/deploy.js --network {network}` in onchain/ first."
            )
        deployment = json.loads(deployment_path.read_text(encoding="utf-8"))

        self.network = network
        self.chain_id = deployment["chainId"]
        self.web3 = Web3(Web3.HTTPProvider(rpc_url, request_kwargs={"timeout": 20}))

        if not self.web3.is_connected():
            raise OnchainBridgeUnavailable(f"Cannot reach RPC endpoint for network '{network}'")

        self.account = self.web3.eth.account.from_key(private_key)

        self.contracts: dict[str, Any] = {}
        for name in CONTRACT_NAMES:
            address = deployment["contracts"][name]
            abi = self._load_abi(onchain_dir, name)
            self.contracts[name] = self.web3.eth.contract(address=address, abi=abi)

    @staticmethod
    def _load_abi(onchain_dir: Path, contract_name: str) -> list[dict[str, Any]]:
        artifact_path = onchain_dir / "artifacts" / "contracts" / f"{contract_name}.sol" / f"{contract_name}.json"
        if not artifact_path.exists():
            raise OnchainBridgeUnavailable(
                f"Compiled artifact missing for {contract_name}: {artifact_path}. "
                f"Run `npx hardhat compile` in onchain/."
            )
        artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
        return artifact["abi"]

    # ------------------------------------------------------------------
    # Writes (synchronous — call via asyncio.to_thread from async code)
    # ------------------------------------------------------------------

    def anchor_block(self, poa_block_index: int, poa_block_hash_hex: str) -> str:
        """Anchors a local PoA block hash on-chain. Returns the tx hash (hex)."""
        contract = self.contracts["PoAAnchor"]
        hash_bytes32 = self._to_bytes32(poa_block_hash_hex)
        tx_hash = self._send(contract.functions.anchorBlock(poa_block_index, hash_bytes32))
        logger.info("onchain: anchored PoA block %s (hash=%s) tx=%s", poa_block_index, poa_block_hash_hex, tx_hash)
        return tx_hash

    def record_anomaly(self, meter_id: str, attack_type: str, confidence: float, poa_block_hash_hex: str) -> str:
        """Records one anomaly directly on-chain. `confidence` is 0..1 and
        is stored on-chain as basis points (0..10000). Returns the tx hash
        (hex)."""
        contract = self.contracts["AnomalyRegistry"]
        confidence_bps = max(0, min(10000, round(confidence * 10000)))
        hash_bytes32 = self._to_bytes32(poa_block_hash_hex)
        tx_hash = self._send(contract.functions.recordAnomaly(meter_id, attack_type, confidence_bps, hash_bytes32))
        logger.info(
            "onchain: recorded anomaly meter=%s type=%s confidence=%.2f tx=%s",
            meter_id, attack_type, confidence, tx_hash,
        )
        return tx_hash

    # ------------------------------------------------------------------
    # Reads
    # ------------------------------------------------------------------

    def status(self) -> dict[str, Any]:
        anomaly_registry = self.contracts["AnomalyRegistry"]
        poa_anchor = self.contracts["PoAAnchor"]
        authority_registry = self.contracts["AuthorityRegistry"]
        return {
            "enabled": True,
            "network": self.network,
            "chain_id": self.chain_id,
            "account": self.account.address,
            "balance_eth": float(self.web3.from_wei(self.web3.eth.get_balance(self.account.address), "ether")),
            "contracts": {name: contract.address for name, contract in self.contracts.items()},
            "anomaly_record_count": anomaly_registry.functions.recordCount().call(),
            "last_anchored_poa_index": poa_anchor.functions.lastAnchoredIndex().call(),
            "anchor_count": poa_anchor.functions.anchorCount().call(),
            "authority_count": authority_registry.functions.authorityCount().call(),
        }

    def verify_anchor(self, poa_block_index: int, poa_block_hash_hex: str) -> bool:
        contract = self.contracts["PoAAnchor"]
        return bool(contract.functions.verifyAnchor(poa_block_index, self._to_bytes32(poa_block_hash_hex)).call())

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    @staticmethod
    def _to_bytes32(hex_hash: str) -> bytes:
        clean = hex_hash[2:] if hex_hash.startswith("0x") else hex_hash
        return bytes.fromhex(clean.rjust(64, "0")[-64:])

    def _send(self, function_call: Any) -> str:
        nonce = self.web3.eth.get_transaction_count(self.account.address, "pending")
        tx = function_call.build_transaction({"from": self.account.address, "nonce": nonce, "chainId": self.chain_id})
        signed = self.account.sign_transaction(tx)
        raw = getattr(signed, "raw_transaction", None) or getattr(signed, "rawTransaction")
        tx_hash = self.web3.eth.send_raw_transaction(raw)
        return tx_hash.hex()


_bridge: OnchainBridge | None = None
_bridge_init_attempted = False


def get_onchain_bridge() -> OnchainBridge | None:
    """Process-wide singleton, lazily constructed. Returns None (never
    raises) if the bridge is disabled or misconfigured — callers must
    treat a None return as "on-chain features unavailable" and continue
    without them, exactly like `inference_service_url` being unset skips
    the external inference microservice."""
    global _bridge, _bridge_init_attempted
    if _bridge is not None:
        return _bridge
    if _bridge_init_attempted:
        return None
    _bridge_init_attempted = True

    from production.config.settings import get_settings

    settings = get_settings()

    if not settings.onchain_enabled:
        return None
    if not settings.onchain_rpc_url or not settings.onchain_private_key:
        logger.warning("onchain: SGRID_ONCHAIN_ENABLED=1 but RPC URL or private key missing — bridge disabled")
        return None

    try:
        _bridge = OnchainBridge(
            onchain_dir=Path(settings.onchain_dir),
            network=settings.onchain_network,
            rpc_url=settings.onchain_rpc_url,
            private_key=settings.onchain_private_key,
        )
        logger.info("onchain: bridge initialized on network '%s'", settings.onchain_network)
    except OnchainBridgeUnavailable as exc:
        logger.warning("onchain: bridge unavailable: %s", exc)
        _bridge = None

    return _bridge


def reset_onchain_bridge() -> None:
    """Test hook — forces re-initialization on the next get_onchain_bridge() call."""
    global _bridge, _bridge_init_attempted
    _bridge = None
    _bridge_init_attempted = False

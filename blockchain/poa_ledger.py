"""Proof-of-Authority ledger for smart-meter CSV data.

This module anchors smart-meter readings into an append-only blockchain-like
ledger. It is intentionally lightweight and local: the CSV remains the source
of truth, while the chain stores row hashes, block hashes, and authority
signatures for traceability and tamper detection.
"""

from __future__ import annotations

import csv
import hashlib
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Sequence

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
from cryptography.hazmat.primitives.serialization import Encoding, NoEncryption, PrivateFormat, PublicFormat


ZERO_HASH = "0" * 64


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _canonical_json(payload: Any) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _chunked(items: Sequence[Any], size: int) -> Iterable[Sequence[Any]]:
    if size <= 0:
        raise ValueError("block size must be greater than zero")

    for start in range(0, len(items), size):
        yield items[start : start + size]


@dataclass(frozen=True)
class AuthorityNode:
    """A validator authorized to seal blocks in the PoA network.

    SECURITY (fixed in Phase 8.5): signing uses a real Ed25519 keypair.
    `public_key` (hex) is safe to expose — it is what `summary()`/
    `/api/blockchain/status` would need to publish for third-party
    verification, though today only `label` is exposed there. The private
    key lives only in memory for this object's lifetime and is excluded
    from equality/hashing/repr (`compare=False, repr=False`) so it can
    never leak through an accidental `asdict()`/log/print of this
    dataclass. Previously, `secret` was `sha256(label + fixed-suffix)` —
    fully recomputable by anyone who read the source or the public label
    (itself returned by the API), which defeated the ledger's own
    tamper-evidence claim. See
    `thesis_package/review/ieee_style_final_review.md` §3 for the finding
    that prompted this fix, and
    `production/docs/key_rotation_and_recovery.md` for key management.
    """

    label: str
    public_key: str  # hex-encoded Ed25519 public key — safe to expose
    _private_key: Ed25519PrivateKey | None = field(default=None, repr=False, compare=False)

    @classmethod
    def from_label(cls, label: str) -> "AuthorityNode":
        """Generates a FRESH random Ed25519 keypair for this label.

        Suitable for tests and throwaway/isolated ledgers (nothing needs
        to survive past this process). Production code that needs a
        persistent authority identity across process restarts must use
        `from_label_and_private_key` with a key obtained via
        `production.security.authority_keys.load_or_generate_authority_keys()`
        instead of calling this directly.
        """
        normalized = label.strip() or "Authority"
        return cls._build(normalized, Ed25519PrivateKey.generate())

    @classmethod
    def from_label_and_private_key(cls, label: str, private_key_bytes: bytes) -> "AuthorityNode":
        """Builds a node from a caller-supplied 32-byte Ed25519 private key —
        the persistent-identity path used by production (see
        `production/security/authority_keys.py`)."""
        normalized = label.strip() or "Authority"
        return cls._build(normalized, Ed25519PrivateKey.from_private_bytes(private_key_bytes))

    @classmethod
    def _build(cls, label: str, private_key: Ed25519PrivateKey) -> "AuthorityNode":
        public_bytes = private_key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
        return cls(label=label, public_key=public_bytes.hex(), _private_key=private_key)

    def seal(self, block_hash: str) -> str:
        if self._private_key is None:
            raise RuntimeError(f"AuthorityNode '{self.label}' has no private key loaded; cannot sign")
        return self._private_key.sign(block_hash.encode("utf-8")).hex()

    def verify(self, block_hash: str, signature_hex: str) -> bool:
        """Verifies a signature using only this node's PUBLIC key — the
        correct asymmetric-crypto property that `validate()` now relies on
        instead of recomputing a shared secret."""
        try:
            public_key = Ed25519PublicKey.from_public_bytes(bytes.fromhex(self.public_key))
            public_key.verify(bytes.fromhex(signature_hex), block_hash.encode("utf-8"))
            return True
        except (InvalidSignature, ValueError):
            return False


@dataclass
class PoABlock:
    index: int
    timestamp: str
    previous_hash: str
    proposer: str
    authority_signature: str
    transaction_root: str
    transaction_count: int
    alert_count: int
    normal_count: int
    row_start: int
    row_end: int
    source_file: str
    transactions: list[dict[str, Any]] = field(default_factory=list)
    block_hash: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class ProofOfAuthorityLedger:
    """Build and validate a private Proof-of-Authority chain from CSV rows."""

    def __init__(
        self,
        authorities: Sequence[AuthorityNode] | None = None,
        block_size: int = 100,
        source_file: str = "unknown.csv",
    ) -> None:
        if block_size <= 0:
            raise ValueError("block_size must be greater than zero")

        self.authorities = list(authorities) if authorities else [
            AuthorityNode.from_label("Utility Operator"),
            AuthorityNode.from_label("Grid Supervisor"),
            AuthorityNode.from_label("Security Auditor"),
            AuthorityNode.from_label("Data Custodian"),
        ]
        if not self.authorities:
            raise ValueError("at least one authority is required")

        self.block_size = block_size
        self.source_file = source_file
        self.chain: list[PoABlock] = []
        self._build_genesis_block()

    @classmethod
    def from_csv(
        cls,
        csv_path: str | Path,
        block_size: int = 100,
        max_rows: int | None = None,
        authorities: Sequence[AuthorityNode] | None = None,
    ) -> "ProofOfAuthorityLedger":
        path = Path(csv_path)
        ledger = cls(authorities=authorities, block_size=block_size, source_file=path.name)
        records = ledger.load_csv_records(path, max_rows=max_rows)
        ledger.ingest_records(records)
        return ledger

    @staticmethod
    def load_csv_records(csv_path: str | Path, max_rows: int | None = None) -> list[dict[str, Any]]:
        path = Path(csv_path)
        if not path.exists():
            raise FileNotFoundError(f"CSV file not found: {path}")

        records: list[dict[str, Any]] = []
        with path.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            for row_index, row in enumerate(reader, start=1):
                if max_rows is not None and row_index > max_rows:
                    break

                normalized = {
                    key: (value.strip() if value is not None else "")
                    for key, value in row.items()
                }
                record: dict[str, Any] = {"row_index": row_index, **normalized}
                record["row_hash"] = _sha256_text(_canonical_json(record))
                records.append(record)

        return records

    def ingest_records(self, records: Sequence[dict[str, Any]]) -> None:
        for batch in _chunked(records, self.block_size):
            self.chain.append(self._build_block(list(batch)))

    def validate(self) -> tuple[bool, list[str]]:
        errors: list[str] = []
        authority_map = {authority.label: authority for authority in self.authorities}

        for index, block in enumerate(self.chain):
            if block.transaction_count != len(block.transactions):
                errors.append(
                    f"Block {block.index}: transaction_count mismatch ({block.transaction_count} != {len(block.transactions)})"
                )

            expected_root = self._transaction_root(block.transactions)
            if block.transaction_root != expected_root:
                errors.append(f"Block {block.index}: transaction root mismatch")

            proposer = authority_map.get(block.proposer)
            if proposer is None:
                errors.append(f"Block {block.index}: unknown proposer '{block.proposer}'")
            elif not proposer.verify(block.block_hash, block.authority_signature):
                errors.append(f"Block {block.index}: invalid authority signature")

            if index == 0:
                if block.previous_hash != ZERO_HASH:
                    errors.append("Genesis block has an invalid previous hash")
            else:
                previous_block = self.chain[index - 1]
                if block.previous_hash != previous_block.block_hash:
                    errors.append(
                        f"Block {block.index}: previous hash mismatch"
                    )

            expected_hash = self._hash_block_payload(block)
            if block.block_hash != expected_hash:
                errors.append(f"Block {block.index}: block hash mismatch")

            if block.row_start > block.row_end:
                errors.append(f"Block {block.index}: invalid row range")

        return (len(errors) == 0, errors)

    def summary(self) -> dict[str, Any]:
        data_blocks = self.chain[1:]
        total_transactions = sum(block.transaction_count for block in data_blocks)
        total_alerts = sum(block.alert_count for block in data_blocks)
        total_normals = sum(block.normal_count for block in data_blocks)

        return {
            "source_file": self.source_file,
            "block_size": self.block_size,
            "authorities": [authority.label for authority in self.authorities],
            "total_blocks": len(self.chain),
            "data_blocks": len(data_blocks),
            "total_transactions": total_transactions,
            "total_alerts": total_alerts,
            "total_normals": total_normals,
            "latest_block_hash": self.chain[-1].block_hash if self.chain else "",
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "metadata": {
                "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
                **self.summary(),
            },
            "chain": [block.to_dict() for block in self.chain],
        }

    def save(self, output_path: str | Path, block_dir: str | Path | None = None) -> Path:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as handle:
            json.dump(self.to_dict(), handle, indent=2, ensure_ascii=False)

        if block_dir is not None:
            self.save_blocks(block_dir)

        return path

    def save_blocks(self, block_dir: str | Path) -> Path:
        path = Path(block_dir)
        path.mkdir(parents=True, exist_ok=True)

        block_files: list[str] = []
        block_hash_rows: list[dict[str, Any]] = []
        for block in self.chain:
            block_path = path / self._block_filename(block)
            with block_path.open("w", encoding="utf-8") as handle:
                json.dump(block.to_dict(), handle, indent=2, ensure_ascii=False)
            block_files.append(block_path.name)
            block_hash_rows.append(self._block_hash_entry(block))

        manifest = {
            "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
            "source_file": self.source_file,
            "block_size": self.block_size,
            "block_count": len(self.chain),
            "block_files": block_files,
            "block_hash_file": "block_hashes.csv",
            **self.summary(),
        }
        manifest_path = path / "manifest.json"
        with manifest_path.open("w", encoding="utf-8") as handle:
            json.dump(manifest, handle, indent=2, ensure_ascii=False)

        block_hash_path = path / "block_hashes.csv"
        legacy_hash_path = path / "block_hashes.json"
        if legacy_hash_path.exists():
            legacy_hash_path.unlink()
        with block_hash_path.open("w", encoding="utf-8", newline="") as handle:
            fieldnames = [
                "block_type",
                "index",
                "block_file",
                "timestamp",
                "row_start",
                "row_end",
                "transaction_count",
                "alert_count",
                "normal_count",
                "previous_hash",
                "transaction_root",
                "block_hash",
                "authority_signature",
                "proposer",
                "source_file",
            ]
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            for row in block_hash_rows:
                writer.writerow(row)

        return path

    def _build_genesis_block(self) -> None:
        genesis_transactions: list[dict[str, Any]] = []
        proposer = self.authorities[0]
        timestamp = datetime.fromtimestamp(0, tz=timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
        transaction_root = self._transaction_root(genesis_transactions)
        block = PoABlock(
            index=0,
            timestamp=timestamp,
            previous_hash=ZERO_HASH,
            proposer=proposer.label,
            authority_signature="",
            transaction_root=transaction_root,
            transaction_count=0,
            alert_count=0,
            normal_count=0,
            row_start=0,
            row_end=0,
            source_file="genesis",
            transactions=genesis_transactions,
        )
        block.block_hash = self._hash_block_payload(block)
        block.authority_signature = proposer.seal(block.block_hash)
        self.chain.append(block)

    def _build_block(self, transactions: list[dict[str, Any]]) -> PoABlock:
        block_index = len(self.chain)
        proposer = self.authorities[block_index % len(self.authorities)]
        timestamp = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
        row_start = int(transactions[0]["row_index"])
        row_end = int(transactions[-1]["row_index"])
        alert_count = sum(1 for record in transactions if str(record.get("statut", "")).upper() == "ALERTE")
        normal_count = len(transactions) - alert_count
        transaction_root = self._transaction_root(transactions)
        block = PoABlock(
            index=block_index,
            timestamp=timestamp,
            previous_hash=self.chain[-1].block_hash,
            proposer=proposer.label,
            authority_signature="",
            transaction_root=transaction_root,
            transaction_count=len(transactions),
            alert_count=alert_count,
            normal_count=normal_count,
            row_start=row_start,
            row_end=row_end,
            source_file=self.source_file,
            transactions=transactions,
        )
        block.block_hash = self._hash_block_payload(block)
        block.authority_signature = proposer.seal(block.block_hash)
        return block

    def _transaction_root(self, transactions: Sequence[dict[str, Any]]) -> str:
        if not transactions:
            return _sha256_text("GENESIS")

        joined_hashes = "|".join(str(record["row_hash"]) for record in transactions)
        return _sha256_text(joined_hashes)

    def _hash_block_payload(self, block: PoABlock) -> str:
        payload = {
            "index": block.index,
            "timestamp": block.timestamp,
            "previous_hash": block.previous_hash,
            "proposer": block.proposer,
            "transaction_root": block.transaction_root,
            "transaction_count": block.transaction_count,
            "alert_count": block.alert_count,
            "normal_count": block.normal_count,
            "row_start": block.row_start,
            "row_end": block.row_end,
            "source_file": block.source_file,
        }
        return _sha256_text(_canonical_json(payload))

    def _block_filename(self, block: PoABlock) -> str:
        if block.index == 0:
            return "block_0000_genesis.json"

        return (
            f"block_{block.index:04d}_rows_{block.row_start:06d}_{block.row_end:06d}.json"
        )

    def _block_hash_entry(self, block: PoABlock) -> dict[str, Any]:
        return {
            "block_type": "GENESIS" if block.index == 0 else "DATA",
            "index": block.index,
            "block_file": self._block_filename(block),
            "timestamp": block.timestamp,
            "row_start": block.row_start,
            "row_end": block.row_end,
            "transaction_count": block.transaction_count,
            "alert_count": block.alert_count,
            "normal_count": block.normal_count,
            "previous_hash": block.previous_hash,
            "transaction_root": block.transaction_root,
            "block_hash": block.block_hash,
            "authority_signature": block.authority_signature,
            "proposer": block.proposer,
            "source_file": block.source_file,
        }

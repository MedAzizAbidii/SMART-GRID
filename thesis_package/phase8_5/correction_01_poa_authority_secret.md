# Correction #1 — PoA Authority Secret Vulnerability

## 1. Problem

The Proof-of-Authority blockchain ledger's block-signing scheme derived
each authority's signing "secret" **deterministically from public
information**: `sha256(f"{label}|smart-grid-poa-secret")`, where `label`
is one of four fixed strings returned directly by the public
`/api/blockchain/status` endpoint, and the suffix is a hardcoded literal
in open source code. Anyone who read the repository or the API's own
response could recompute all four "secrets" and forge a validly-signed
block. This was first identified during the Phase 8 IEEE-style final
review (`thesis_package/review/ieee_style_final_review.md`, §3).

## 2. Root Cause

`AuthorityNode.from_label()` in `blockchain/poa_ledger.py` treated a
one-way hash of public data as if it were a secret. A hash of known
inputs is not a secret merely because it is expressed as a hex digest —
anyone with the same inputs (the label and the fixed suffix, both
knowable) reproduces the identical value. The design conflated "looks
like a cryptographic value" with "is actually secret," and used symmetric
recomputation (`seal()` recomputes and string-compares) where asymmetric
signing (private key never shared, public key used to verify) was
required.

## 3. Files Modified

- `blockchain/poa_ledger.py` — `AuthorityNode` class rewritten to hold a
  real Ed25519 keypair; `validate()` updated to verify via public key.
- `production/security/authority_keys.py` — **new file**: secure key
  generation/persistence (env var or git-ignored local file, auto-
  generated on first run).
- `api_server.py` — `_live_ledger` construction now calls
  `load_or_generate_authority_keys()` instead of `AuthorityNode.from_label()`
  directly.
- `.gitignore` — added `authority_keys.json` alongside the existing
  `users.json`-style secret exclusions.
- `production/docker/docker-compose.yml` — added a named volume so
  authority keys persist across container recreation (a consideration
  this fix itself introduced for the Docker topology).
- `production/docs/key_rotation_and_recovery.md` — **new file**.

## 4. Exact Code Changes

**`blockchain/poa_ledger.py`** — `AuthorityNode` before:
```python
@dataclass(frozen=True)
class AuthorityNode:
    label: str
    secret: str

    @classmethod
    def from_label(cls, label: str) -> "AuthorityNode":
        normalized = label.strip() or "Authority"
        secret = _sha256_text(f"{normalized}|smart-grid-poa-secret")
        return cls(label=normalized, secret=secret)

    def seal(self, block_hash: str) -> str:
        return _sha256_text(f"{self.secret}:{block_hash}")
```

After (abridged — full version in the file):
```python
@dataclass(frozen=True)
class AuthorityNode:
    label: str
    public_key: str  # hex-encoded Ed25519 public key — safe to expose
    _private_key: Ed25519PrivateKey | None = field(default=None, repr=False, compare=False)

    @classmethod
    def from_label(cls, label: str) -> "AuthorityNode":
        normalized = label.strip() or "Authority"
        return cls._build(normalized, Ed25519PrivateKey.generate())

    @classmethod
    def from_label_and_private_key(cls, label: str, private_key_bytes: bytes) -> "AuthorityNode":
        normalized = label.strip() or "Authority"
        return cls._build(normalized, Ed25519PrivateKey.from_private_bytes(private_key_bytes))

    def seal(self, block_hash: str) -> str:
        if self._private_key is None:
            raise RuntimeError(f"AuthorityNode '{self.label}' has no private key loaded; cannot sign")
        return self._private_key.sign(block_hash.encode("utf-8")).hex()

    def verify(self, block_hash: str, signature_hex: str) -> bool:
        try:
            public_key = Ed25519PublicKey.from_public_bytes(bytes.fromhex(self.public_key))
            public_key.verify(bytes.fromhex(signature_hex), block_hash.encode("utf-8"))
            return True
        except (InvalidSignature, ValueError):
            return False
```

**`validate()`** before: `expected_signature = proposer.seal(block.block_hash); if block.authority_signature != expected_signature: ...`
After: `elif not proposer.verify(block.block_hash, block.authority_signature): ...`

**`api_server.py`** before:
```python
_live_ledger = ProofOfAuthorityLedger(
    authorities=[AuthorityNode.from_label("Utility Operator"), ...],
    block_size=10, source_file="live_alerts")
```
After:
```python
_live_ledger = ProofOfAuthorityLedger(
    authorities=load_or_generate_authority_keys(),
    block_size=10, source_file="live_alerts")
```

## 5. Security Impact

**Closed**: the previously-forgeable signature scheme. Verified directly
(see §8) that recomputing the old derivable "secret" no longer produces a
signature that `verify()` accepts. Signing now requires possession of a
private key that is never derivable from public data and never
transmitted or exposed via any API response.

**New consideration introduced by the fix, addressed**: private keys must
now be persisted somewhere outside source code; a lost/rotated key
invalidates verification of prior exports (documented in
`key_rotation_and_recovery.md`, not silently glossed over).

**Not addressed by this fix** (out of scope, noted honestly): single-
signer-per-block (round-robin, no quorum/multisig) still means compromise
of the currently-proposing authority's key alone is sufficient to forge a
block during that authority's turn. Moving to threshold/multisig
authority approval would be a design change beyond "fix the vulnerability
found," not attempted here.

## 6. Scientific Impact

**None.** No model, dataset, experiment, or benchmark result is touched.
The PoA ledger is infrastructure for tamper-evident notarization of
confirmed detections, entirely downstream of the AI pipeline's output —
changing how a block is *signed* has no bearing on how an anomaly is
*detected* or *scored*. All Phase 0-7 scientific conclusions and reported
metrics are unaffected and unchanged.

## 7. Production Impact

**Blockchain functionality preserved**: `ingest_records()`,
`validate()`, `save()`, `from_csv()`, and the `ProofOfAuthorityLedger`
constructor signature are all unchanged. `/api/blockchain/status`'s
response shape (`available`, `valid`, `blocks`, `authorities`) is
identical. The notarization workflow triggered from `_finalize_detection()`
is unchanged.

**New operational requirement**: `production/security/authority_keys.json`
(or the four `SGRID_AUTHORITY_KEY_*` env vars) must now be backed up and
persisted like any other secret (see `key_rotation_and_recovery.md`) — a
genuinely new operational responsibility that did not exist under the old
(insecure) scheme, which needed no key management because it had no real
keys.

## 8. Validation Steps

1. `./.venv/Scripts/python.exe -m pytest production/tests/ -q` → 46/46 pass (unchanged).
2. Direct ledger test: build a ledger, ingest a record, confirm
   `validate()` returns `(True, [])`.
3. **Attack reproduction test** (confirms the fix): recompute the OLD
   derivable secret (`sha256("Utility Operator|smart-grid-poa-secret")`),
   attempt to use it as a forged signature via `proposer.verify(...)` →
   returns `False` (previously this exact recomputation would have
   produced a byte-identical, ACCEPTED "signature" under the old scheme).
4. Tamper-detection regression check: mutate a block's `transaction_count`
   after signing, confirm `validate()` still catches it (unrelated to
   signing, but must not have broken) → correctly flagged.
5. Key persistence test: call `load_or_generate_authority_keys()` twice
   in separate processes, confirm identical public keys returned both
   times (proves persistence, not fresh-random-every-call).
6. Environment-variable override test: set
   `SGRID_AUTHORITY_KEY_UTILITY_OPERATOR`, confirm it takes priority over
   the file-persisted key for that authority.
7. Live server smoke test: fresh `api_server.py` start,
   `/api/blockchain/status` → `"valid": true`, same 4 authority labels as
   before.

## 9. Before/After Comparison

| Aspect | Before | After |
|---|---|---|
| Signing mechanism | `sha256(secret + block_hash)`, secret = `sha256(label + fixed_suffix)` | Ed25519 asymmetric signature |
| Can an attacker who reads the source/API forge a block? | **Yes** — secret fully recomputable from public data | **No** — verified: recomputed old-style "secret" is rejected by `verify()` |
| Key storage | None (no real key existed) | Git-ignored local file (auto-generated) or env var |
| `/api/blockchain/status` response shape | `{available, valid, blocks, authorities}` | **Identical** |
| `ProofOfAuthorityLedger` public API | `ingest_records`, `validate`, `save`, `from_csv`, constructor | **Identical** |
| Test suite | 46/46 passing | 46/46 passing (unchanged) |
| Signature length (hex) | 64 chars (SHA-256 digest) | 128 chars (Ed25519 signature) — a visible, expected format change for anyone inspecting raw block JSON |

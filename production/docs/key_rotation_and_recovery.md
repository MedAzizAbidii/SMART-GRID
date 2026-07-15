# PoA Authority Key — Rotation & Recovery Procedures

Covers the Ed25519 authority signing keys introduced in Phase 8.5
(`production/security/authority_keys.py`), fixing the vulnerability where
authority "secrets" were previously derivable from public labels (see
`thesis_package/review/ieee_style_final_review.md` §3 for the original
finding).

## How keys are stored

- **Default (local dev / single-node)**: `production/security/
  authority_keys.json`, a git-ignored JSON file mapping each authority
  label to a base64-encoded 32-byte Ed25519 private key. Auto-generated
  on first run if missing.
- **Production override**: environment variables
  `SGRID_AUTHORITY_KEY_UTILITY_OPERATOR`, `SGRID_AUTHORITY_KEY_GRID_SUPERVISOR`,
  `SGRID_AUTHORITY_KEY_SECURITY_AUDITOR`, `SGRID_AUTHORITY_KEY_DATA_CUSTODIAN`
  — each a base64-encoded 32-byte Ed25519 private key. Takes priority over
  the file for any authority whose env var is set. Intended for
  injection via your platform's secret manager (Kubernetes Secret, Docker
  secret, HashiCorp Vault, etc.) rather than left on a container's disk.

**Public keys are safe to expose** (they are what verification needs);
private keys must never be logged, printed, or committed. The
`AuthorityNode` dataclass excludes the private key from `repr()`/equality
specifically to make accidental leakage into logs harder.

## Generating a new key manually

```bash
./.venv/Scripts/python.exe -c "
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PrivateFormat, NoEncryption
import base64
priv = Ed25519PrivateKey.generate()
raw = priv.private_bytes(Encoding.Raw, PrivateFormat.Raw, NoEncryption())
print(base64.b64encode(raw).decode())
"
```

Set the output as the relevant `SGRID_AUTHORITY_KEY_<LABEL>` environment
variable, or paste it into `authority_keys.json` under the matching label
key.

## Key rotation procedure

Rotating an authority's key is a deliberate, infrequent operation (suspected
compromise, scheduled security hygiene, personnel change for that
authority role) — not part of routine operation.

1. **Generate a new key** for the authority being rotated (see above).
2. **Stop the server** (or the specific container). The PoA chain is
   in-memory and rebuilt fresh on every process start (documented
   pre-existing behavior, unrelated to this fix) — there is currently no
   "hot rotation" of a running chain's signing identity, and building one
   is out of scope for this correction (would be a new feature, not a
   fix).
3. **Update the key source**: either set the new `SGRID_AUTHORITY_KEY_<LABEL>`
   env var (recommended for production), or edit `authority_keys.json`
   directly for that authority's entry.
4. **Restart the server.** `load_or_generate_authority_keys()` will load
   the new key for that authority and continue using the existing keys
   for the other three.
5. **Verify**: `curl http://localhost:8000/api/blockchain/status` should
   report `"valid": true` for the fresh chain (a new genesis block signed
   with the rotated key set).
6. **Discard the old key material securely** — remove it from wherever it
   was previously stored (old env var value, old JSON file backup) once
   you've confirmed the new key works.

**Important**: blocks signed by the OLD key before rotation remain
verifiable only against the OLD public key. If you have archived/exported
chain data (via `ledger.save()`) signed before a rotation, keep a record of
which public key was active for which time period if you need to
re-verify historical exports later — this ledger implementation does not
currently version authority keys over time (a documented limitation, not
a bug: the live in-memory chain resets on every restart regardless of key
rotation, so this matters mainly for exported/archived chain snapshots).

## Recovery procedure (lost or corrupted key file)

**If `authority_keys.json` is lost and no env vars are set**: on the next
server start, `load_or_generate_authority_keys()` will generate a
**brand-new** set of 4 keys automatically — the server will come back up
and function normally (new genesis block, new signing identity). This is
by design: availability is prioritized over forcing a manual recovery
step for what is, today, in-memory-only chain state.

**What you lose**: the ability to verify signatures on any PREVIOUSLY
EXPORTED chain snapshot (`ledger.save()` output) that was signed with the
lost keys — those exports become historically un-reverifiable (though
still readable as plain JSON; only the cryptographic signature check
against the old public keys is affected, not the data itself).

**To prevent this class of loss going forward**:
- Prefer the environment-variable path for any deployment where the
  container filesystem is ephemeral (the default local-file path is only
  as durable as whatever volume it sits on — see the Docker volume note
  in `docker_validation.md`).
- Back up `authority_keys.json` using the same procedure as
  `production/security/users.json` and `.env`, documented in
  `backup_restore.md` — treat it as equally sensitive secret material,
  not as regular application data.

**If you need to recover a SPECIFIC prior identity** (not just "any
working set of keys"): restore `authority_keys.json` (or the env vars)
from your secret backup rather than letting auto-generation create a new
set — auto-generation is a fallback for availability, not a substitute
for backing up keys you actually care about preserving.

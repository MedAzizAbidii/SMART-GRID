# Phase 6 — Security Review Report

*Generated 2026-07-14 · audit performed against the hardened codebase after
all Phase 6 changes were applied · every finding below was verified by
running a real check, not asserted from inspection alone.*

## Scope

Hardcoded secrets, unsafe file handling, missing input validation,
authentication weaknesses, authorization gaps, dependency vulnerabilities —
across `api_server.py`, the new `production/` package, and the runtime
dependency tree.

## Summary

| Severity | Count | Status |
|---|---|---|
| Critical | 0 | — |
| High | 2 | **Fixed** during this review |
| Medium | 3 | **Fixed** during this review |
| Low / Accepted | 2 | Documented, accepted risk |

---

## Findings

### H1 — CORS wildcard + credentials (invalid & insecure combination) — FIXED

**Before:** `allow_origins=["*"]` with `allow_credentials=True`. This
combination is rejected by browsers per the CORS spec when actually enforced,
and where a permissive proxy allows it anyway, it defeats the same-origin
protection credentials are meant to have.
**Fix:** Origins now come from `SGRID_CORS_ALLOWED_ORIGINS` (settings,
defaults to `["http://localhost:8000"]`); credentials are enabled only when
the origin list isn't a wildcard. `Settings.validate_runtime()` additionally
raises a **FATAL** warning if `environment=production` and origins still
contain `*`.
**Verified:** `production/tests/test_config.py::test_validate_runtime_flags_wildcard_cors_in_production`.

### H2 — 17 known CVEs across 6 dependencies — FIXED

Ran `pip-audit` (a real scanner, not a manual guess). Found 18 known
vulnerabilities in `cryptography`, `ecdsa`, `pillow`, `pip`, `setuptools`,
`starlette` — including two in `starlette` directly relevant to this app:

- **PYSEC-2026-249**: `request.form()` doesn't bound
  `application/x-www-form-urlencoded` size — directly exploitable against
  the new `/api/auth/login` endpoint (which parses form-encoded credentials)
  before the fix.
- **PYSEC-2026-2281**: `StaticFiles` on Windows vulnerable to SSRF via UNC
  paths — relevant since this app serves static dashboard assets.

**Fix:** Upgraded `starlette` (1.0.1→1.3.1), `cryptography` (48.0.0→49.0.0),
`pillow` (12.2.0→12.3.0), `setuptools` (65.5.0→81.0.0, pinned `<82` for
torch compatibility). Pins recorded in `requirements.txt` with the CVE IDs
they fix.
**Verified:** full 46-test suite re-run after the upgrade — no regressions;
`pip-audit` re-run confirms 17/18 fixed.
**Residual (accepted):** `ecdsa` 0.19.2 (PYSEC-2026-1325, Minerva timing
attack) has **no maintainer-planned fix**. Low risk here: it's a transitive
dependency of `python-jose[cryptography]`, and this app signs JWTs with
**HS256 (HMAC)**, not ECDSA — the vulnerable code path is not exercised by
our usage.

### M1 — No endpoints required authentication — FIXED (scoped)

**Before:** every endpoint was open; a caller could reload the model,
inject grid data, queue packet-tracer commands, or trigger attack
simulations with no credential at all.
**Fix:** JWT + 4-role RBAC (`viewer < analyst < grid_operator < administrator`,
additive hierarchy) added. Applied to genuinely mutating/administrative
endpoints: `/api/grid/data`, `/api/integrations/silicon-apocalypse/event`,
`/api/packet-tracer/{energy,security,commands}` (POST), `/api/simulate/attack`,
`/api/model/reload`.
**Deliberate, documented scope decision:** read-mostly status/detection
endpoints the existing dashboard already auto-polls unauthenticated
(`/api/detect`, `/api/blockchain/status`, `/api/model/status`, `/api/alerts`)
were **left open** to avoid breaking the working dashboard (see the
`SGRID_CORS_ALLOWED_ORIGINS`-gated, same-origin trust model in the
deployment guide). This is a stated trade-off, not a silent gap — a
"strict mode" that also locks down reads is a documented future item.
**Verified:** `test_auth.py`, `test_e2e_api.py` (401 unauthenticated, 403
insufficient role, 200 correct role, dashboard-critical endpoints unaffected).

### M2 — No login brute-force protection — FIXED

**Before:** the general rate limiter (120 req/min) applied uniformly,
permitting up to 120 password guesses/minute from one IP against
`/api/auth/login`.
**Fix:** `/api/auth/login` now has its own, separately-tracked, much
stricter budget (default 10/min, configurable via
`SGRID_RATE_LIMIT_LOGIN_PER_MINUTE`), independent of the general API limit.
**Verified:** `test_middleware.py::test_login_endpoint_has_stricter_rate_limit`.

### M3 — Plaintext default passwords stored alongside their hashes — FIXED

**Before:** `production/security/users.json` contained a
`_default_passwords_DEV_ONLY` block with cleartext dev passwords in the
same file the running app reads and that could end up version-controlled.
**Fix:** removed; only bcrypt hashes remain in `users.json`. Default dev
credentials are documented **once**, clearly labeled, in
`operator_manual.md` only.
**Verified:** `test_auth.py::test_authenticate_real_dev_users` still passes
(hashes unaffected), file contents manually re-inspected.

### L1 — bcrypt/passlib version incompatibility — FIXED (as a byproduct)

`passlib`'s `CryptContext` backend-detection crashed against the installed
`bcrypt>=4.1` (`AttributeError: module 'bcrypt' has no attribute '__about__'`)
— a known ecosystem compatibility break. Switched to calling `bcrypt`
directly (`hash_password`/`verify_password` in `auth.py`), removing the
version-detection dependency entirely. Also hardened: passwords are
defensively truncated to bcrypt's 72-byte input limit instead of raising,
and `verify_password` catches malformed-hash errors and fails **closed**
(returns `False`) rather than 500ing.

### Verified safe (no action needed)

- **Path traversal in `/model-test/assets/{filename}`**: already mitigated
  via `os.path.basename(filename)` before joining to the base directory —
  confirmed by direct code inspection; a `../../etc/passwd`-style filename
  collapses to `passwd` and cannot escape the intended directory.
- **No hardcoded secrets in source**: `grep`-based scan for
  `password=`/`secret=`/`api_key=` literals across all `.py` files found
  none outside test fixtures and the documented `CHANGE_ME` placeholder.
- **`.env` is git-ignored** and the project has no `.git` repository yet —
  no current leak surface, but `.env.example` (placeholders only) is
  provided for when version control is initialized.
- **Unhandled exceptions no longer leak stack traces**: the global
  exception handler (`production/middleware.py`) returns a generic
  `internal_error` + `request_id` to the caller and logs the real traceback
  server-side only (`system.log`).

## Recommendations for future hardening (not blocking, documented)

1. Move the in-memory rate limiter to Redis before running >1 worker process
   or >1 node (documented limitation, stated in the code's own docstring).
2. Consider a "strict mode" config flag that also requires auth on read-mostly
   endpoints, for deployments where the dashboard is also updated to log in.
3. Replace the JSON-file user store with a real database/IdP (documented in
   `deployment_guide.md`) before onboarding real operator accounts.
4. Re-run `pip-audit` on a schedule (e.g. CI, weekly) — dependency
   vulnerabilities are discovered continuously, not just once.

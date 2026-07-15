# Changelog

All notable changes to this project are documented in this file.

## [v1.0.0-thesis] — Repository freeze for thesis submission

### Fixed (Phase 8.5 — final engineering corrections)

- **Security**: PoA blockchain authority signing keys were previously
  derived deterministically from public labels
  (`sha256(label + fixed_suffix)`), making them recomputable by anyone
  with source or API access — defeating the ledger's tamper-evidence
  claim. Replaced with real Ed25519 keypairs, persisted outside source
  code (env var or git-ignored local file, auto-generated on first run).
  See `thesis_package/phase8_5/correction_01_poa_authority_secret.md`.
- **Performance**: `/api/detect` and `/api/detect/batch` called blocking
  model inference directly inside `async def` handlers, serializing all
  concurrent requests on a single worker (throughput measured degrading
  from 5.04 req/s at 10 concurrent requests to 2.37 req/s at 1000).
  Offloaded to a worker thread via `asyncio.to_thread`, with a per-meter
  lock added to preserve identical prediction outputs under genuine
  concurrency. See
  `thesis_package/phase8_5/correction_02_async_concurrency.md`.
- **Performance**: `/health/detailed` called
  `psutil.cpu_percent(interval=0.1)`, blocking the event loop for ~100ms
  on every call (measured accounting for ~99% of the endpoint's ~109ms
  latency), polled every 5s by the dashboard's health widget. Replaced
  with the non-blocking `interval=None` pattern (primed once at module
  load). Latency reduced to ~4-18ms; response shape unchanged. See
  `thesis_package/phase8_5/correction_03_blocking_health_endpoint.md`.
- **Infrastructure**: `docker-compose.yml`'s `backend` service now
  persists PoA authority keys across container recreation via a named
  volume — a consideration introduced by the security fix above, applied
  proactively to the Docker topology even though it remains unbuilt. See
  `thesis_package/phase8_5/correction_04_docker_verification.md`.

### Added

- `production/security/authority_keys.py` — secure key generation/
  persistence for PoA authority identities.
- `production/docs/key_rotation_and_recovery.md`.
- `production/docs/docker_validation.md`.
- `perf/bench_phase8_5_reprofile.py` — before/after performance
  re-profiling for the two fixed bottlenecks.
- `thesis_package/` — complete thesis (20 chapters, French), defense
  material, IEEE publication package, GitHub package, architecture/UML
  diagrams (17 total), and an IEEE-reviewer-style final critical review
  that identified the PoA vulnerability fixed in this release.
- `perf/` — Phase 7 performance-profiling suite (latency, throughput,
  concurrency, endurance benchmarks; see
  `perf/reports/phase7_performance_report.md`).

### Changed

- `.gitignore` — added `authority_keys.json` alongside the existing
  `users.json` secret-exclusion pattern.

### Known limitations carried into this release (not fixed, by design/scope)

- Mobile application, Solidity smart contracts, and Firebase push are not
  implemented — the original PFE subject's IA+Blockchain pillars are
  complete and validated; the mobile pillar is not (see
  `thesis_package/thesis/chapitre_18_limitations.md`).
- The deployed model artifacts (`outputs/early_stopping_final`,
  `outputs/test_run_now`) predate the Phase 0 leak-free evaluation
  protocol fix — retraining under the corrected protocol was explicitly
  out of scope for this release ("Do NOT retrain any model").
- Docker topology is still not build-verified (no Docker available on
  the development machine); a ready-to-run validation procedure is
  documented instead of fabricated results.
- The PoA ledger's single-signer-per-block design (no quorum/multisig)
  was not changed — only the derivability of the signing key was fixed.

---

## Previous phases (summarized; full detail in `thesis_package/thesis/`)

- **Phase 0** — Data-leakage diagnosis and fix (leak-free temporal split
  protocol).
- **Phase 1** — Benchmark against 6 baseline models.
- **Phase 2 / 2.5** — Ablation study (38 configurations) and dedicated
  investigation of the attention-neutrality finding.
- **Phase 3 / 4** — Robustness, adversarial, and calibration evaluation.
- **Phase 5** — Real-data validation on the SGCC public fraud dataset.
- **Phase 6** — Production hardening (auth, RBAC, logging, monitoring,
  security audit: 17/18 CVEs fixed).
- **Phase 7** — End-to-end performance profiling.
- **Phase 8** — Thesis, defense, publication, and GitHub packages; the
  IEEE-reviewer-style final review that surfaced the vulnerability fixed
  in Phase 8.5.
- **Phase 8.5** — This release: final engineering corrections and
  repository freeze.

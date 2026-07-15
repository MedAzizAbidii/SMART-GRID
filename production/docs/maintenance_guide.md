# Maintenance Guide

## Routine

| Task | Frequency | Command |
|---|---|---|
| Dependency vulnerability scan | Weekly / before each release | `.\.venv\Scripts\python.exe -m pip_audit` |
| Full test suite | Every change | `.\.venv\Scripts\python.exe -m pytest production\tests\ -q` |
| Log review | Daily (or via log aggregation) | `logs/system.log`, `logs/attacks.log` |
| Blockchain validation | Weekly | `curl http://localhost:8000/api/blockchain/status` — check `"valid": true` |
| Recalibration (if drift suspected) | As needed | See the scientific-phase `calibration/recalibrate.py` — **outside Phase 6 scope**, do not run casually; it changes the detection threshold |

## Log rotation

Automatic — 5 files, each rotates at 10MB, keeps 5 backups
(`SGRID_LOG_MAX_BYTES` / `SGRID_LOG_BACKUP_COUNT`). No manual `logrotate`
setup needed for the default topology; if you redirect stdout/stderr to a
container log driver too, that's a second, separate rotation policy (Docker's
own `json-file` driver has its own `max-size`/`max-file` options — set them
in `docker-compose.yml` if container-log volume becomes a concern).

## Dependency updates

1. `pip list --outdated`
2. Upgrade one package at a time, re-run the full test suite after each.
3. Re-run `pip_audit` — confirm the CVE you were fixing is actually gone
   (some advisories require a specific patch version, not just "newer").
4. Watch for `torch`'s `setuptools<82` constraint (hit this during Phase 6 —
   see `security_report.md` finding H2) — verify no new conflicts before
   committing an upgrade.

## Model lifecycle (read this before touching anything model-related)

The scientific evaluation (Phases 0-5) is **frozen** per the Phase 6 brief.
This guide's model-related actions are limited to:
- **Reload** (`/api/model/reload`) — re-reads the same trained weights from
  disk, no retraining.
- **Recalibration** — a documented, separate script (`calibration/recalibrate.py`
  from Phase 4/0) that only touches the decision threshold, not weights.

Retraining, re-benchmarking, or re-ablating the model is **out of scope**
for this production layer — those live in `ablation/`, `benchmark/`,
`realdata/`, etc., and are governed by the scientific-phase constraints.

## Health-check failure runbook

1. `curl /health` fails entirely → process is down; check container/service
   logs, restart.
2. `/health` OK but `/health/ready` returns 503 → check `checks.model_loaded`
   and `checks.blockchain_available` in the response body; `system.log` will
   have the specific load error.
3. `/health/detailed` shows `blockchain.valid: false` → the PoA chain failed
   its own validation (tampered or corrupted); do not keep writing to it —
   investigate `blockchain.error_count` and the underlying `data/blockchain/`
   files before restarting.

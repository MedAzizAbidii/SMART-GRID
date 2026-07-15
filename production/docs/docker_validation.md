# Docker Validation — Status and Procedure

**Status: NOT executed.** Docker is not installed on this development
machine (verified during this Phase 8.5 pass: `docker --version` resolves
to no command). Per this phase's explicit instruction, no build/run
results are fabricated below — everything in this document is either a
static-review fact (already true, verified by reading the files) or an
exact command to run on a Docker-enabled machine, with the output that
command is *expected* to produce, clearly labeled as expected rather than
observed.

## What has been verified (static review, no Docker required)

| Check | Result |
|---|---|
| `docker-compose.yml` — valid YAML | ✓ Parses cleanly (verified via `python -c "import yaml; yaml.safe_load(open('production/docker/docker-compose.yml'))"`) |
| Every `COPY` source path in `Dockerfile.backend` exists in the repo | ✓ (`api_server.py`, `config.py`, `ml_pipeline/`, `blockchain/`, `dashboard/`, `production/`, `outputs/early_stopping_final/`, `outputs/test_run_now/`) |
| Every `COPY` source path in `Dockerfile.inference` exists | ✓ (`ml_pipeline/`, `outputs/`, `production/config/`, `production/inference_service.py`, `production/__init__.py`) |
| Every `COPY` source path in `Dockerfile.dashboard` exists | ✓ |
| `requirements-inference.txt` / `requirements-dev.txt` import lists match actual imports used by the files each container runs | ✓ (matched against `api_server.py` and `production/inference_service.py`) |
| Non-root user configured (`Dockerfile.backend`) | ✓ (`useradd appuser`, `USER appuser`) |
| Healthchecks defined for all 3 services | ✓ |
| **Phase 8.5**: authority key persistence survives a container restart | ✓ Fixed during this pass — a named volume `authority_keys` was added, mounted at `/app/production/security` in the `backend` service (`docker-compose.yml`). Without it, a fresh container would auto-generate NEW Ed25519 keys on every restart, silently invalidating verification of any previously-notarized blocks. For a real deployment, prefer the `SGRID_AUTHORITY_KEY_*` env vars (see `authority_keys.py`) injected via your orchestrator's secret manager instead of this file-backed volume, which is the local-dev-equivalent default — the volume mount is still correct as a fallback/local-dev path. **Still unverified by an actual build** (see status line above), so confirm the mount behaves as expected the first time Docker is available.

## Exact commands to run on a Docker-enabled machine

```bash
cd smartgrid_simulation/production/docker

# 1. Build all three images
docker compose build

# Expected output: three successful builds, ending with something like:
#   [+] Building 3/3
#    ✔ inference  Built
#    ✔ backend    Built
#    ✔ dashboard  Built

# 2. Start the stack
docker compose up -d

# Expected output:
#   [+] Running 4/4
#    ✔ Network docker_smartgrid  Created
#    ✔ Container docker-inference-1  Started
#    ✔ Container docker-backend-1    Started
#    ✔ Container docker-dashboard-1  Started

# 3. Wait for health, then check status
docker compose ps
# Expected: all 3 services show "healthy" within ~30-60s (start_period
# in each Dockerfile's HEALTHCHECK: 20s inference, 30s backend).
```

## Validation checklist (run against the started stack)

```bash
# API — direct
curl http://localhost:8000/health
# Expected: {"status":"alive","uptime_seconds":<number>}

curl http://localhost:8000/health/ready
# Expected: {"status":"ready","checks":{"model_loaded":true,"blockchain_available":true}}

# Inference service — direct (only reachable if SGRID_INFERENCE_SERVICE_URL
# routes backend -> inference; confirm this env var is set in
# docker-compose.yml's backend service before assuming this topology is
# actually exercised rather than falling back to in-process inference)
curl http://localhost:8100/health
# Expected: {"status":"alive",...}

# Dashboard — through nginx proxy
curl -I http://localhost:8080/dashboard
# Expected: HTTP/1.1 200 OK

curl http://localhost:8080/api/blockchain/status
# Expected (proxied through nginx to backend):
# {"available":true,"valid":true,"blocks":<n>,"authorities":[...]}
# — the 4 authority labels should be unchanged from a non-Docker run;
#   the underlying signing keys will differ per §"authority key
#   persistence" above unless a volume/env-var is configured.

# Authentication
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"<see users.json>","password":"<see users.json>"}'
# Expected: {"access_token":"...","token_type":"bearer"}

# Detection endpoint (send >= seq_len readings for the same meter_id to
# get past "insufficient_data")
curl -X POST http://localhost:8000/api/detect \
  -H "Content-Type: application/json" \
  -d '{"meter_id":"SM_DOCKER_TEST","consommation_kw":2.3,"tension_v":228,"courant_a":10.1,"zone":"Zone A","type":"residentiel"}'
# Expected: {"meter_id":"SM_DOCKER_TEST","status":"insufficient_data",...}
# on the first calls, then a full detection result once seq_len readings
# have been sent.
```

## Known assumptions (stated, not hidden)

1. The compose file has **not** been build-verified even once end-to-end
   — every step above is a static, file-level review plus the standard,
   documented behavior of Docker Compose and each base image
   (`python:3.10-slim`, `nginx`), not an observed run on this project's
   specific code.
2. `torch` and other heavy dependencies in `Dockerfile.backend`/
   `Dockerfile.inference` will download from PyPI during `docker compose
   build` — first build time is expected to be several minutes,
   dependent on network speed; this has not been timed.
3. The authority-key persistence gap above (§ table) is a **new** finding
   from this Phase 8.5 pass, not carried over from Phase 6 — Phase 6
   never needed to consider key persistence since it predates the
   Ed25519 key-management fix.
4. If this checklist is run and any step fails, the failure should be
   recorded in this same file (a new "## Actual run — <date>" section
   appended below) rather than silently discarded — turning this from a
   procedure into a real validation record the next time Docker is
   available.

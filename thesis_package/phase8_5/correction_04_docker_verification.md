# Correction #4 — Docker Verification

## 1. Problem

The 3-container Docker topology (`production/docker/`) had never been
build-verified — reviewed only statically (path existence, YAML syntax,
import matching) since no Docker-enabled machine was available during
Phase 6 or Phase 7.

## 2. Root Cause

Environmental: Docker is not installed on this development machine
(confirmed again during this pass — `docker --version` resolves to no
command). Not a code defect.

## 3. Files Modified

- `production/docker/docker-compose.yml` — added a named volume
  (`authority_keys`) mounted at `/app/production/security` in the
  `backend` service, so Correction #1's persistent authority keys
  actually persist across container recreation in the Docker topology too
  (a consideration Correction #1 introduced; without this, every
  container restart would silently generate new signing keys).
- `production/docs/docker_validation.md` — **new file**.

## 4. Exact Code Changes

`docker-compose.yml`, `backend` service, `volumes:` before:
```yaml
    volumes:
      - ../../../data:/data
      - backend_logs:/app/logs
```
After:
```yaml
    volumes:
      - ../../../data:/data
      - backend_logs:/app/logs
      - authority_keys:/app/production/security
```
And top-level `volumes:` before: `backend_logs:` — after: `backend_logs:`
+ `authority_keys:`.

Per this phase's explicit instruction, **no build/run results are
fabricated**. `production/docs/docker_validation.md` instead contains the
exact commands to run, the output expected from each, a validation
checklist, and known assumptions — ready to execute the first time
Docker is available, with a placeholder section to append real results
into rather than treating this document as a one-time deliverable.

## 5. Security Impact

The volume-mount fix prevents a real (if narrow) security regression that
Correction #1 would otherwise have introduced specifically in the Docker
topology: without it, a container restart would silently rotate all
authority keys, which — combined with the Docker topology's use of the
same `docker-compose.yml` across restarts — could produce confusing
false "invalid signature" states on any block signed before the restart,
or mask the fact that a rotation happened at all if nobody is watching
`/api/blockchain/status`.

## 6. Scientific Impact

None.

## 7. Production Impact

**Containerization readiness is unchanged from Phase 6's own assessment**
(55/100, the lowest dimension in the production-readiness table) — this
correction improves the compose file's correctness for one specific new
concern (key persistence) but does not itself constitute a build
verification. The action item stands: build-test on a Docker-enabled
machine before relying on this topology.

## 8. Validation Steps

1. YAML re-validated after the edit:
   `python -c "import yaml; yaml.safe_load(open('production/docker/docker-compose.yml'))"`
   → parses cleanly, `volumes` section shows both `backend_logs` and
   `authority_keys`, `backend.volumes` includes the new mount line.
2. No other validation is possible without Docker itself — stated
   directly rather than worked around.

## 9. Before/After Comparison

| Aspect | Before | After |
|---|---|---|
| Docker build/run verified | No | **Still no** — honestly unchanged; this correction only improves compose-file correctness and documentation |
| Authority key persistence across container restarts | Would have silently regenerated on every restart (an oversight, since Correction #1 postdates the original compose file) | Persisted via named volume |
| Validation procedure documented | No dedicated document | `production/docs/docker_validation.md` — exact commands, expected output, checklist, assumptions |

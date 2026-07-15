# Deployment Guide

## Topology options

### 1. Single process (simplest — what runs today by default)

```powershell
.\.venv\Scripts\python.exe api_server.py
```

The AI model loads in-process (`get_detector()`), the dashboard is served
from the same process, blockchain runs in-memory. Suitable for a single
demo/lab machine.

### 2. Three containers (Docker Compose) — inference / backend / dashboard separated

**Not verified on this development machine (Docker was not installed here).**
Dockerfiles and `docker-compose.yml` were validated by:
- static review of every `COPY` source path (all confirmed to exist),
- YAML syntax validation (`yaml.safe_load` — passed),
- confirming `api_server.py`'s actual imports match exactly what each
  Dockerfile copies (no more, no less).

**Run this smoke test on a Docker-enabled machine before relying on it:**

```bash
cd smartgrid_simulation/production/docker
docker compose up --build
# wait for all 3 healthchecks to go "healthy": docker compose ps
curl http://localhost:8100/health          # inference
curl http://localhost:8000/health          # backend
curl http://localhost:8080/                # dashboard (nginx)
curl -X POST http://localhost:8080/api/detect -H "Content-Type: application/json" \
  -d '{"meter_id":"SM_0001","zone":"Zone A","type":"industriel","consommation_kw":14,"tension_v":227,"courant_a":62}'
# confirm this reaches inference via the backend proxy:
docker compose logs inference | tail -5
```

If any healthcheck fails, `docker compose logs <service>` first —
the most likely failure mode is a missing `outputs/early_stopping_final/`
or `outputs/test_run_now/` directory (the trained model artifacts are not
committed to source control by default in some setups; confirm they exist
in `smartgrid_simulation/outputs/` before building).

Services:
| Service | Port | Purpose |
|---|---|---|
| `inference` | 8100 | AI model only (`production/inference_service.py`) |
| `backend` | 8000 | FastAPI API, proxies `/api/detect` to `inference` |
| `dashboard` | 8080 | nginx, static UI + reverse-proxy to `backend` |

### 3. Backend-only container (model in-process, no separate inference service)

```bash
docker build -f production/docker/Dockerfile.backend -t smartgrid-backend .
docker run -p 8000:8000 -v $(pwd)/../data:/data smartgrid-backend
```

Leave `SGRID_INFERENCE_SERVICE_URL` unset — the backend image includes
`ml_pipeline/` + the trained model directories and runs everything in-process,
identical to topology #1 but containerized.

## Environment setup for staging/production

1. `cp .env.example .env`, generate a real `SGRID_JWT_SECRET_KEY`.
2. Set `SGRID_ENVIRONMENT=production`.
3. Set `SGRID_CORS_ALLOWED_ORIGINS` to your real dashboard origin(s) —
   never `["*"]` (blocked by `validate_runtime()`).
4. Replace `production/security/users.json` with real accounts (see
   `administrator_manual.md` — user management).
5. Mount `data/` as a persistent volume (blockchain ledger, meter data) —
   never bake it into an image.

## Rollback

Images are tagged by version (`smartgrid-backend:1.0.0` etc.) — `docker
compose down` then re-`up` with the previous tag. There is no automated
blue-green/canary mechanism; this is a documented gap (see
`security_report.md` recommendations and the Phase-6 final limitations).

## Scaling notes

The in-memory rate limiter and PoA ledger are per-process state — running
more than one `backend` replica requires moving both to a shared store
(Redis for rate limiting; the blockchain ledger already has a durable
JSON-file save/load path in `blockchain/poa_ledger.py` that a shared
deployment should point at a common volume).

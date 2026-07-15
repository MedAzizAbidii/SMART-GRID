# Configuration Guide

All configuration is centralized in `production/config/settings.py`
(pydantic-settings), loaded from environment variables prefixed `SGRID_`, or
a `.env` file in `smartgrid_simulation/`. Nothing is hardcoded elsewhere —
if a value should be configurable, it belongs here.

## Startup validation

`Settings.validate_runtime()` is called once at server startup and logs
every problem to `system.log`. In `SGRID_ENVIRONMENT=production`, two
conditions are **FATAL** (should block a real deployment, currently logged
as warnings — wire to a hard exit in your process supervisor if desired):
the JWT secret is still the default, or CORS origins include a wildcard.

## Reference

| Variable | Default | Notes |
|---|---|---|
| `SGRID_ENVIRONMENT` | `development` | `development`\|`staging`\|`production` |
| `SGRID_DEBUG` | `false` | |
| `SGRID_API_HOST` | `0.0.0.0` | |
| `SGRID_API_PORT` | `8000` | |
| `SGRID_CORS_ALLOWED_ORIGINS` | `["http://localhost:8000"]` | JSON array; never `["*"]` in production |
| `SGRID_RATE_LIMIT_REQUESTS_PER_MINUTE` | `120` | general API, per client IP |
| `SGRID_RATE_LIMIT_LOGIN_PER_MINUTE` | `10` | separate, stricter budget for `/api/auth/login` |
| `SGRID_JWT_SECRET_KEY` | insecure dev placeholder | **generate a real one**: `python -c "import secrets; print(secrets.token_urlsafe(48))"` |
| `SGRID_JWT_ALGORITHM` | `HS256` | |
| `SGRID_JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | `60` | |
| `SGRID_USERS_FILE` | `production/security/users.json` | swap for a DB/IdP in production (see `deployment_guide.md`) |
| `SGRID_MODEL_DIR_V3` | `outputs/early_stopping_final` | high-precision model |
| `SGRID_MODEL_DIR_V2` | `outputs/test_run_now` | high-recall model (ensemble) |
| `SGRID_DETECTION_THRESHOLD_OVERRIDE` | unset | override the trained threshold if set |
| `SGRID_INFERENCE_SERVICE_URL` | unset | if set, `/api/detect` proxies here instead of running in-process |
| `SGRID_BLOCKCHAIN_BLOCK_SIZE` | `20` | rows per PoA block |
| `SGRID_LOG_DIR` | `logs` | 5 rotating JSON log files (see `maintenance_guide.md`) |
| `SGRID_LOG_LEVEL` | `INFO` | |
| `SGRID_LOG_MAX_BYTES` | `10000000` | 10MB per file before rotation |
| `SGRID_LOG_BACKUP_COUNT` | `5` | rotated backups kept |
| `SGRID_METRICS_ENABLED` | `true` | Prometheus `/metrics` |

## Validating a configuration change

```powershell
.\.venv\Scripts\python.exe -c "
from production.config.settings import Settings
s = Settings()
print(s.model_dump())
print('problems:', s.validate_runtime())
"
```

## Legacy settings (pre-Phase-6, still respected)

- `SMARTGRID_API_KEY` (env var, not `.env`-file-backed): if set, requires
  header `X-API-Key` on `/api/model/reload` and `/api/simulate/attack`, in
  addition to (not instead of) the new JWT role requirement.

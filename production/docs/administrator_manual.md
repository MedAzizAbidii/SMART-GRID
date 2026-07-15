# Administrator Manual

## User management

Users live in `production/security/users.json` (bcrypt hashes only — never
plaintext, see `security_report.md` finding M3). There is no admin UI or API
endpoint for user management yet (documented gap); add/change users by
regenerating the file:

```powershell
.\.venv\Scripts\python.exe -c "
import json
from production.security.auth import hash_password
from pathlib import Path

path = Path('production/security/users.json')
data = json.loads(path.read_text())
data['users'].append({
    'username': 'new_operator',
    'password_hash': hash_password('a-strong-real-password'),
    'role': 'grid_operator',   # viewer | analyst | grid_operator | administrator
    'full_name': 'New Operator Name',
})
path.write_text(json.dumps(data, indent=2))
"
```

Changes take effect immediately — `authenticate_user()` reads the file on
every login attempt (no restart needed, no in-memory cache to invalidate).

**Roles** (additive hierarchy — each inherits everything below it):
`viewer` < `analyst` < `grid_operator` < `administrator`.

## Reloading the model

After running `recalibrate.py` or retraining (see the scientific-phase
READMEs — **do not** retrain via this production layer; that's out of
Phase 6's scope and would invalidate the frozen scientific results):

```bash
curl -X POST http://localhost:8000/api/model/reload \
  -H "Authorization: Bearer <admin_token>"
```

Reloads `outputs/early_stopping_final` + `outputs/test_run_now` from disk
without restarting the process.

## Configuration changes

Edit `.env`, restart the process (settings are read once at import time —
there's a `reload_settings()` helper in `production/config/settings.py` for
programmatic reload in a REPL/test, but the running server does not
hot-reload `.env` changes).

## Logs — what's where

| File | Contents |
|---|---|
| `logs/app.log` | server lifecycle (startup, config) |
| `logs/predictions.log` | every scored reading |
| `logs/attacks.log` | confirmed anomalies only |
| `logs/blockchain.log` | ledger writes/validation |
| `logs/system.log` | errors, exceptions, config problems |

Each is JSON, one object per line, rotating at 10MB × 5 backups
(`SGRID_LOG_MAX_BYTES` / `SGRID_LOG_BACKUP_COUNT`). Every line carries a
`request_id` — grep the same ID across all 5 files to reconstruct one
incident end-to-end.

## Monitoring integration

`/metrics` is real Prometheus exposition format (via `prometheus_client`) —
point a standard Prometheus scrape config at it:

```yaml
scrape_configs:
  - job_name: smartgrid
    static_configs: [{targets: ["backend:8000"]}]
```

Falls back to a plain-JSON summary automatically if `prometheus_client`
isn't installed in a given environment (no hard dependency).

## Backup & restore

See `backup_restore.md`.

## Security posture

See `security_report.md` for the full audit; re-run `pip-audit` periodically
(dependencies aren't a one-time check).

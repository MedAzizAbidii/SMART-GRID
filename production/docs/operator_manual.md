# Operator Manual

For day-to-day use of the dashboard and detection system. If you need to
manage user accounts or server configuration, see `administrator_manual.md`.

## Logging in

Default accounts (**change these before any non-local use** — see
"Changing your password" below; there is currently no self-service password
change endpoint, so this means asking an administrator to regenerate your
hash — see `administrator_manual.md`):

| Username | Password | Role | Can do |
|---|---|---|---|
| `viewer` | `ChangeMe-Viewer-2026!` | viewer | View dashboard, status, alerts |
| `analyst` | `ChangeMe-Analyst-2026!` | analyst | + run `/api/simulate/attack` |
| `operator` | `ChangeMe-Operator-2026!` | grid_operator | + ingest grid/packet-tracer data & commands |
| `admin` | `ChangeMe-Admin-2026!` | administrator | + reload the model |

Get a token:

```bash
curl -X POST http://localhost:8000/api/auth/login \
  -d "username=analyst&password=ChangeMe-Analyst-2026!"
# -> {"access_token": "...", "token_type": "bearer", "role": "analyst"}
```

Use it: `-H "Authorization: Bearer <access_token>"`. Tokens expire after 60
minutes (`SGRID_JWT_ACCESS_TOKEN_EXPIRE_MINUTES`) — log in again.

## The dashboard

http://localhost:8000/dashboard (or `:8080` in the 3-container topology).
No login is required to *view* the dashboard (see `security_report.md`
finding M1 for why) — it auto-polls detection/status/blockchain endpoints.
Triggering an attack simulation or issuing packet-tracer commands from the
dashboard's own UI still requires the underlying API call to carry a valid
token if you've wired the dashboard's forms to do so (default dashboard
build does not — those actions are exposed via the raw API and `curl`/`docs`
today, not a dashboard button; see the new "Operational Dashboard" panels
in `dashboard/index.html`'s health/status widgets for what IS live there
without extra wiring).

## Checking system health

- `/health` — is the process alive at all
- `/health/ready` — is the model loaded and blockchain available
- `/health/detailed` — CPU/RAM, model latency, blockchain block count
- `/api/blockchain/status` — ledger validity + block count
- `/api/model/status` — which model version, threshold, latency

## Reviewing detections

- `/api/alerts` — recent alert history
- `logs/attacks.log` — every confirmed, non-deduplicated anomaly, structured
  JSON, one line per event, with `meter_id`, `attack_type`, `confidence`
- `logs/predictions.log` — every single reading scored (not just attacks) —
  useful for auditing false negatives after the fact

## Simulating an attack (requires `analyst` role or higher)

```bash
curl -X POST "http://localhost:8000/api/simulate/attack?bus_id=3&attack_type=fdia&magnitude=0.3&duration=30" \
  -H "Authorization: Bearer <token>"
```

## What to do if...

- **"model_unavailable" on /api/detect`**: model failed to load at startup —
  check `logs/system.log` for the exact error, confirm
  `outputs/early_stopping_final/` exists.
- **429 "rate_limited"**: you've exceeded 120 req/min (general) or 10/min
  (login specifically) from your IP. Wait a minute.
- **401/403 on a protected endpoint**: log in again (token expired) or your
  role is below what the action requires (see the role table above).

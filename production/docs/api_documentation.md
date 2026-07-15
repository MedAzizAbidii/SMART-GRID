# API Documentation

Full interactive OpenAPI docs are auto-generated and always up to date at
`/docs` (Swagger UI) and `/redoc` — this file is a curated overview, not a
duplicate of the schema.

## Authentication

```
POST /api/auth/login   (form: username, password)  -> {access_token, role}
GET  /api/auth/me      (Bearer token)               -> {username, role}
```

All protected endpoints expect `Authorization: Bearer <token>` and respond
`401` (no/invalid token) or `403` (valid token, insufficient role).

## Core detection

| Endpoint | Method | Auth | Purpose |
|---|---|---|---|
| `/api/detect` | POST | open | Score one smart-meter reading |
| `/api/detect/batch` | POST | open | Score up to 100 readings |
| `/api/model/status` | GET | open | Loaded model, threshold, latency |
| `/api/model/thresholds` | GET | open | Per-meter adaptive thresholds |
| `/api/model/registry` | GET | open | All registered model versions |
| `/api/model/reload` | POST | `administrator` + `X-API-Key` if set | Reload model from disk |

## Grid / simulation

| Endpoint | Method | Auth |
|---|---|---|
| `/api/grid/all`, `/api/grid/bus/{id}` | GET | open |
| `/api/grid/data` | POST | `grid_operator` |
| `/api/simulate/attack` | POST | `analyst` (+ `X-API-Key` if set) |
| `/api/packet-tracer/status`, `/commands` (GET) | GET | open |
| `/api/packet-tracer/{energy,security}`, `/commands` (POST) | POST | `grid_operator` |
| `/api/integrations/silicon-apocalypse/event` | POST | `grid_operator` |

## Blockchain

| Endpoint | Method | Auth |
|---|---|---|
| `/api/blockchain/status` | GET | open |

## Monitoring (Phase 6)

| Endpoint | Method | Auth |
|---|---|---|
| `/health` | GET | open, never rate-limited |
| `/health/ready` | GET | open, never rate-limited |
| `/health/detailed` | GET | open, never rate-limited |
| `/metrics` | GET | open, never rate-limited |

## Response shape (every endpoint, consistently)

Success: the endpoint's own schema (see `/docs`).
Error (any failure mode — validation, HTTP, or unhandled exception):
```json
{"error": "validation_error|http_error|internal_error|rate_limited|...",
 "detail": "...", "request_id": "a1b2c3d4e5f6"}
```
Every response also carries `X-Request-ID` and `X-Response-Time-ms` headers.

## Rate limits

120 req/min general, 10 req/min on `/api/auth/login` specifically (both
per client IP; `/health` and `/metrics` are exempt). Exceeding either
returns `429` with the same `{error, detail, request_id}` shape.

## WebSocket

`ws://.../ws` — send `"get_data"` / `"get_alerts"` / `"ping"` text frames,
receive JSON. Unauthenticated (matches the dashboard's existing usage;
not modified by Phase 6).

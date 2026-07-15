# Correction #3 — Blocking Health Endpoint

## 1. Problem

`/health/detailed` called `psutil.cpu_percent(interval=0.1)` synchronously
inside an `async def` route with no executor offload. Phase 7 profiling
measured this single call accounting for ~99% of the endpoint's ~109ms
mean latency, blocking the entire event loop (not just the requesting
connection) for ~100ms on every call — polled every 5 seconds by the
dashboard's own health widget (Phase 6), meaning the whole server froze
for ~100ms every 5 seconds purely from this one monitoring call.

## 2. Root Cause

`psutil.cpu_percent(interval=X)` with a numeric `interval` internally
calls `time.sleep(X)` to measure CPU usage over that window — it is
blocking BY DESIGN when given an interval. psutil's own documented
non-blocking pattern is `interval=None`, which instead returns usage
since the *last* call to `cpu_percent()` (any call, anywhere in the
process) — but the very first call ever made this way returns a
meaningless `0.0`, which is presumably why `interval=0.1` was used
originally: to get a valid number without any special first-call
handling.

## 3. Files Modified

- `production/monitoring/health.py`

## 4. Exact Code Changes

Added at module load time (once, not per-request):
```python
_psutil_primed = _safe_psutil()
if _psutil_primed is not None:
    _psutil_primed.cpu_percent(interval=None)
```

In the `/health/detailed` handler, before:
```python
"cpu_percent": psutil.cpu_percent(interval=0.1),
```
After:
```python
"cpu_percent": psutil.cpu_percent(interval=None),
```

No other line in the handler changed. The response dict's keys
(`cpu_percent`, `memory_mb`, `memory_percent`) and their types
(all numeric) are identical.

## 5. Security Impact

None.

## 6. Scientific Impact

None. This endpoint has no relationship to the detection model, dataset,
or any experiment.

## 7. Production Impact

**No API changes**: same route, same JSON shape, same keys. **No
dashboard changes needed**: the health widget (Phase 6) reads the same
`resources.cpu_percent` field and displays it identically; verified live
(see §8). **Semantic improvement, not just a speed fix**: `interval=None`
reports CPU usage averaged over the time since the *last* call — for an
endpoint polled every 5 seconds, this now reflects genuine utilization
over that real ~5-second window, arguably a more meaningful sample than
the previous artificial 100ms snapshot.

## 8. Validation Steps

1. `./.venv/Scripts/python.exe -m pytest production/tests/ -q` → 46/46 pass.
2. Isolated micro-benchmark: `psutil.cpu_percent(interval=None)` measured
   directly at 0.03–0.08ms per call (i.e., not blocking at all).
3. Live server test: fresh `api_server.py` start, `GET /health/detailed`
   timed via Python `httpx` (not curl, to rule out any client-side
   overhead) across 8 consecutive calls.
4. Response shape diff: confirmed byte-for-byte identical key set to the
   pre-fix response (`status`, `uptime_seconds`, `resources.{cpu_percent,
   memory_mb, memory_percent}`, `model.{loaded,avg_latency_ms}`,
   `blockchain.{available,valid,blocks,error_count}`,
   `prometheus_available`).
5. Dashboard widget verification: the widget's poll interval (5s) and
   field names (`resources.cpu_percent` etc., consumed by
   `dashboard/index.html`'s Phase 6 health widget) are unchanged; no
   dashboard file was touched in this correction.

## 9. Before/After Comparison

| Metric | Before | After |
|---|---|---|
| `/health/detailed` latency (fresh server, 8 samples) | ~109ms mean (Phase 7) | **4–18ms** (this pass; p50 ≈ 8ms) |
| Event-loop blocking per call | ~100ms (entire process frozen) | **0ms** (non-blocking) |
| Response JSON shape | `{status, uptime_seconds, resources:{cpu_percent,memory_mb,memory_percent}, model:{...}, blockchain:{...}, prometheus_available}` | **Identical** |
| Dashboard widget behavior | Displays CPU/memory/model/blockchain status, 5s poll | **Unchanged** — same fields, same widget code |

This is the one fix in this phase whose before/after comparison is fully
clean and environment-independent (unlike Correction #2's absolute
latency numbers): removing a hardcoded 100ms sleep saves ~100ms
regardless of background system load, and the ~10-20x improvement is
directly attributable to this change alone.

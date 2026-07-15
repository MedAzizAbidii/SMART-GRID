# Correction #2 — Async Concurrency Bottleneck

## 1. Problem

`POST /api/detect` is declared `async def` but called the blocking model
inference function (`_ml_detector.ingest()`) directly and synchronously.
Phase 7 profiling measured that concurrent requests, instead of running
in parallel, serialized on a single worker: throughput went from 5.04
req/s at 10 concurrent requests to 2.37 req/s at 1000 (a *degradation*
with increasing load), and at concurrency=10 the p99 latency (2987ms) was
almost exactly 10× a single request's latency — the signature of full
queueing, not parallel execution.

## 2. Root Cause

FastAPI's `async def` handlers run on the single-threaded asyncio event
loop. A synchronous, CPU-bound call made directly inside one (no
`await asyncio.to_thread(...)` / `run_in_executor`) blocks that ONE event
loop for the call's entire duration — during which no other coroutine,
including other requests' handlers, can make progress. With a single
uvicorn worker (this deployment's default), every concurrent `/api/detect`
call therefore queued behind whichever one started first.

## 3. Files Modified

- `api_server.py` — `/api/detect` and `/api/detect/batch` handlers;
  added a per-meter locking helper.

## 4. Exact Code Changes

Added (new helper, placed above the endpoint definitions):
```python
_meter_locks: dict[str, threading.Lock] = {}
_meter_locks_guard = threading.Lock()

def _get_meter_lock(meter_id: str) -> threading.Lock:
    with _meter_locks_guard:
        lock = _meter_locks.get(meter_id)
        if lock is None:
            lock = threading.Lock()
            _meter_locks[meter_id] = lock
        return lock

def _ingest_locked(detector: Any, raw: dict) -> dict:
    lock = _get_meter_lock(str(raw.get("meter_id", "unknown")))
    with lock:
        return detector.ingest(raw)
```

`/api/detect` before: `result = _ml_detector.ingest(raw)`
After: `result = await asyncio.to_thread(_ingest_locked, _ml_detector, raw)`

`/api/detect/batch` before: `for reading in readings: results.append(_ml_detector.ingest(_reading_to_raw(reading)))`
After: the same loop wrapped in a `_run_batch()` closure, executed via
`results = await asyncio.to_thread(_run_batch)`.

**Why the per-meter lock, beyond the minimum "wrap it in to_thread"**:
moving to a thread pool makes GENUINE parallel calls to
`_ml_detector.ingest()` possible for the first time. Previously, accidental
full serialization on the event loop was *also* protecting per-meter state
(the `_buffers` dict inside `RealtimeDetector`) from concurrent mutation.
Without a lock, two requests for the SAME meter arriving at the same
instant could race on that meter's buffer — a correctness regression the
"preserve identical prediction outputs" requirement rules out. The lock
serializes only same-meter requests; different meters still run fully in
parallel.

**Known, explicitly out-of-scope residual risk**: `ZoneAggregator`
(`ml_pipeline/realtime_detector.py`, a module-level singleton updated by
every `ingest()` call) is keyed by *zone*, not by meter — two different
meters in the same zone processed in parallel threads could still race on
that shared aggregate. Fixing this would require touching
`ml_pipeline/realtime_detector.py`, which this phase's instructions
explicitly place off-limits ("Do NOT modify the AI models"). Documented
here rather than silently left unmentioned.

## 5. Security Impact

None. No change to authentication, input validation, or rate limiting.
The per-meter lock dictionary grows unbounded with the number of distinct
`meter_id` values ever seen — a theoretical memory-growth vector if an
attacker could send requests with unlimited distinct fake meter IDs, but
this is bounded by the same input validation as before (Pydantic field
constraints on `meter_id`) and is not a new attack surface introduced by
this fix; noted for completeness.

## 6. Scientific Impact

None. No model, dataset, or experiment is touched. The fix only changes
*how* the same `ingest()` call is scheduled by the API layer, not what it
computes.

## 7. Production Impact

**API interface unchanged**: same route, same request/response schema,
same status codes, same error handling (the `try/except` around the call
is preserved, now wrapping the `await asyncio.to_thread(...)` instead of
the direct call). **Logging unchanged**: `_finalize_detection()` (called
identically either way) still writes to `predictions.log`/`attacks.log`.
**Authentication unchanged**: `/api/detect` remains deliberately
unauthenticated (a documented Phase 6 trade-off, not altered here).

## 8. Validation Steps

1. `./.venv/Scripts/python.exe -m pytest production/tests/ -q` → 46/46 pass.
2. Live smoke test: 30 sequential `/api/detect` calls to the same meter →
   identical response shape, correct `is_anomaly`/`top_features`/
   `attack_type` fields, correct `deduplicated` behavior on blockchain
   notarization.
3. Concurrency shape test (10 parallel calls to 10 DIFFERENT meters):
   response times clustered within ~180ms of each other (not staggered
   across ~2.5s like a queued pattern would produce) — confirms genuine
   parallel execution.
4. Isolated, HTTP-independent test: called `_ingest_locked` via
   `asyncio.to_thread` directly against the loaded detector and compared
   to a direct synchronous call — confirmed `asyncio.to_thread` itself
   adds no meaningful overhead (both paths showed the same underlying
   `ingest()` cost).

## 9. Before/After Comparison

Absolute latency could not be cleanly compared to Phase 7's original
numbers — a confounding environmental factor (this machine's underlying
per-request inference time drifted from ~275ms in the Phase 7 session to
~600-670ms in this one, reproduced identically by a completely isolated
script that imports neither `api_server.py` nor any Phase 8.5-modified
file, proving the drift is unrelated to this fix). The metric that IS
directly comparable and environment-independent is the **spread between
fastest and slowest concurrent request** at a given concurrency level —
the actual signature of serialization:

| Concurrency level | Before (Phase 7) min/max spread | After (Phase 8.5) min/max spread |
|---|---|---|
| 5 concurrent requests | 295.9ms – 1473.9ms (**4.98× spread** — staggered/queued) | 2107.5ms – 2152.7ms (**1.02× spread** — clustered/parallel) |

A 4.98× spread collapsing to 1.02× is the direct, environment-independent
signature of eliminating request serialization — every concurrent request
now starts and finishes together, rather than queueing behind the ones
ahead of it. See `perf/results/phase8_5_reprofile.json` for full raw data
and `perf/results/concurrency.json` (`http_sanity`) for the original
Phase 7 numbers.

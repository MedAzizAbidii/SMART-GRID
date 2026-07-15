"""Phase 7 — concurrency benchmark.

Per the user's explicit direction after a security-classifier block: HTTP-level
concurrency is measured against the real, unmodified production instance only
within its actual 120 req/min rate-limit budget (levels 1/5/10, low volume).
The full requested range (1..1000) is characterized IN-PROCESS, submitting
concurrent calls to the same shared detector instance api_server.py itself
uses (a Python ThreadPoolExecutor against a bounded pool, like a real
worker/connection pool) — zero HTTP, zero interaction with rate limiting or
auth, so no security control is touched, weakened, or bypassed anywhere.

This also directly tests whether concurrent access to the ONE shared,
process-global detector instance is safe — api_server.py's `/api/detect`
calls `_ml_detector.ingest(raw)` synchronously and directly inside an
`async def` handler (no `run_in_executor`/`asyncio.to_thread`), so on a
single uvicorn worker, concurrent requests are serialized by the event loop
regardless of concurrency level. This benchmark measures that behavior
directly instead of assuming it.
"""
from __future__ import annotations

import json
import sys
import time
from collections import deque
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from perf.config import RESULTS_DIR, BASE_URL, CONCURRENCY_LEVELS
from perf.resource_monitor import ResourceMonitor, summarize
from perf.bench_latency import percentiles, _sample_reading


MAX_POOL_WORKERS = 64  # bounded like a real worker/connection pool; 8 logical CPUs on this machine


def _prewarm(detector, meter_id: str, rows: list[dict]) -> None:
    """Directly seeds the rolling buffer(s) with (seq_len - 1) rows so the
    timed call performs exactly one real forward pass, not repeated warmup
    inference. Touches only this throwaway profiling detector instance's
    in-memory state (a dict keyed by meter_id) — no source file, no shared
    production process, no persisted data."""
    targets = [detector]
    if hasattr(detector, "_v2") and hasattr(detector, "_v3"):
        targets = [detector._v2, detector._v3]
    for t in targets:
        t._buffers[meter_id] = deque(list(rows), maxlen=t._buffer_retain)


def bench_concurrency_inprocess(levels: list[int] = CONCURRENCY_LEVELS) -> dict:
    from ml_pipeline.realtime_detector import get_detector
    from data_generation.generate_realistic_dataset import RealisticDatasetGenerator

    detector = get_detector()
    if detector is None:
        return {"name": "concurrency_inprocess", "error": "model not available"}

    gen = RealisticDatasetGenerator(n_meters=20, seed=17)
    real_mid = gen.meters[0]
    seq_len = detector.seq_len
    ts0 = datetime(2026, 6, 15, 15, 0)

    out = {}
    for level in levels:
        meter_ids = [f"SM_CONC_{level}_{j}" for j in range(level)]
        for mid in meter_ids:
            rows = [gen._meter_reading(real_mid, ts0 + timedelta(minutes=2 * w)) for w in range(seq_len - 1)]
            for r in rows:
                r["meter_id"] = mid
            _prewarm(detector, mid, rows)
        final_readings = []
        for mid in meter_ids:
            r = gen._meter_reading(real_mid, ts0 + timedelta(minutes=2 * (seq_len - 1)))
            r["meter_id"] = mid
            final_readings.append(r)

        times = [None] * level
        errs = [None] * level

        def work(idx: int) -> None:
            t0 = time.perf_counter()
            try:
                detector.ingest(final_readings[idx])
            except Exception as exc:  # noqa: BLE001 — recording, not handling
                errs[idx] = repr(exc)
            times[idx] = (time.perf_counter() - t0) * 1000

        pool_workers = min(level, MAX_POOL_WORKERS)
        mon = ResourceMonitor(interval_sec=0.25)
        mon.start()
        t_wall0 = time.perf_counter()
        timed_out = False
        with ThreadPoolExecutor(max_workers=pool_workers) as ex:
            futures = {ex.submit(work, i): i for i in range(level)}
            try:
                for _ in as_completed(futures, timeout=max(60.0, level * 1.5)):
                    pass
            except TimeoutError:
                timed_out = True
        wall_sec = time.perf_counter() - t_wall0
        samples = mon.stop()

        completed = [t for t in times if t is not None]
        n_errors = sum(1 for e in errs if e is not None)
        n_missing = level - len(completed)  # never finished within the timeout window

        out[level] = {
            "pool_workers": pool_workers,
            "wall_sec": round(wall_sec, 2),
            "throughput_req_per_sec": round(level / wall_sec, 2) if wall_sec > 0 else None,
            "latency_ms": percentiles(completed),
            "errors": n_errors,
            "timed_out_or_incomplete": n_missing,
            "timeout_hit": timed_out,
            "resources": summarize(samples),
        }
        print(f"[concurrency] level={level:>4}  wall={wall_sec:7.2f}s  "
              f"throughput={out[level]['throughput_req_per_sec']}/s  "
              f"errors={n_errors}  incomplete={n_missing}")

    return {"name": "concurrency_inprocess (shared detector instance, bounded thread pool)",
            "pool_cap": MAX_POOL_WORKERS, "by_level": out}


def bench_concurrency_http_sanity(levels: list[int] = (1, 5, 10)) -> dict:
    """Low-volume, real-HTTP concurrency sanity check against the live,
    unmodified production instance — stays well inside the 120 req/min
    budget so no request is rejected for reasons unrelated to concurrency."""
    out = {}
    meter_id = "SM_CONC_HTTP"
    with httpx.Client(base_url=BASE_URL, timeout=15.0) as client:
        for i in range(25):
            client.post("/api/detect", json=_sample_reading(meter_id, i))

        for level in levels:
            payloads = [_sample_reading(meter_id, 25 + i) for i in range(level)]
            times = [None] * level
            codes = [None] * level

            def work(idx: int) -> None:
                t0 = time.perf_counter()
                try:
                    r = client.post("/api/detect", json=payloads[idx])
                    codes[idx] = r.status_code
                except Exception:
                    codes[idx] = -1
                times[idx] = (time.perf_counter() - t0) * 1000

            t_wall0 = time.perf_counter()
            with ThreadPoolExecutor(max_workers=level) as ex:
                list(ex.map(work, range(level)))
            wall_sec = time.perf_counter() - t_wall0
            out[level] = {
                "wall_sec": round(wall_sec, 2),
                "throughput_req_per_sec": round(level / wall_sec, 2) if wall_sec > 0 else None,
                "latency_ms": percentiles([t for t in times if t is not None]),
                "status_counts": {str(c): codes.count(c) for c in set(codes)},
            }
            time.sleep(2)  # let the rate-limit window breathe between levels
    return {"name": "concurrency_http_sanity (live production instance, port 8000, within rate budget)",
            "by_level": out}


def run_all() -> dict:
    print("[concurrency] in-process (shared detector, full requested range)...")
    results = {"inprocess": bench_concurrency_inprocess()}
    print("[concurrency] HTTP sanity check (live server, low levels, within rate budget)...")
    results["http_sanity"] = bench_concurrency_http_sanity()

    out_path = RESULTS_DIR / "concurrency.json"
    out_path.write_text(json.dumps(results, indent=2, default=str), encoding="utf-8")
    print(f"[concurrency] written -> {out_path}")
    return results


if __name__ == "__main__":
    run_all()

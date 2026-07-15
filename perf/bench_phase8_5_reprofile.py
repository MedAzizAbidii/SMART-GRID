"""Phase 8.5 — before/after re-profiling of the two fixed bottlenecks.

Re-measures, against the live production instance with the Phase 8.5
fixes applied, exactly the two things Phase 7 flagged:

  1. /health/detailed latency (was ~109ms, dominated by a blocking
     psutil.cpu_percent(interval=0.1) call; now uses interval=None).
  2. /api/detect concurrency behavior (was near-total serialization from
     a blocking call inside an async handler; now asyncio.to_thread).

Same rate-limit discipline as Phase 7: all HTTP calls stay within the
live, unmodified 120 req/min budget — no bypass, no second instance.
Concurrency levels are therefore smaller than Phase 7's in-process range
(which bypassed HTTP entirely); this script measures the REAL end-to-end
HTTP behavior within what the deployed rate limiter actually allows,
which is the operationally relevant comparison for this fix.
"""
from __future__ import annotations

import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from perf.config import RESULTS_DIR, BASE_URL
from perf.bench_latency import percentiles


def bench_health_detailed(n: int = 15) -> dict:
    times = []
    with httpx.Client(base_url=BASE_URL, timeout=10.0) as client:
        for _ in range(n):
            t0 = time.perf_counter()
            r = client.get("/health/detailed")
            assert r.status_code == 200
            times.append((time.perf_counter() - t0) * 1000)
    return {"name": "health_detailed_after_fix_ms", "stats": percentiles(times)}


def bench_concurrency_http(levels: list[int] = (1, 5, 10)) -> dict:
    """Same levels as Phase 7's original concurrency_http_sanity (see
    perf/results/concurrency.json -> http_sanity) for a direct, apples-to-
    apples before/after comparison at identical concurrency levels."""
    meter_prefix = "SM_PHASE85_CONC"
    out = {}
    with httpx.Client(base_url=BASE_URL, timeout=20.0) as client:
        for level in levels:
            meter_ids = [f"{meter_prefix}_{level}_{i}" for i in range(level)]
            ts0 = datetime(2026, 6, 15, 11, 0)
            for mid in meter_ids:
                for i in range(8):
                    client.post("/api/detect", json={
                        "meter_id": mid, "timestamp": (ts0 + timedelta(minutes=2 * i)).isoformat(),
                        "consommation_kw": 2.0, "tension_v": 228.0, "courant_a": 9.0,
                        "power_factor": 0.91, "frequency_hz": 60.0, "zone": "Zone A", "type": "residentiel",
                    })

            payloads = [{
                "meter_id": mid, "timestamp": (ts0 + timedelta(minutes=16)).isoformat(),
                "consommation_kw": 2.1, "tension_v": 228.0, "courant_a": 9.0,
                "power_factor": 0.91, "frequency_hz": 60.0, "zone": "Zone A", "type": "residentiel",
            } for mid in meter_ids]

            def call(p):
                t0 = time.perf_counter()
                r = client.post("/api/detect", json=p)
                return (time.perf_counter() - t0) * 1000, r.status_code

            t_wall0 = time.perf_counter()
            with ThreadPoolExecutor(max_workers=level) as ex:
                results = list(ex.map(call, payloads))
            wall_sec = time.perf_counter() - t_wall0

            times = [t for t, _ in results]
            codes = [c for _, c in results]
            out[level] = {
                "wall_sec": round(wall_sec, 2),
                "throughput_req_per_sec": round(level / wall_sec, 2) if wall_sec > 0 else None,
                "latency_ms": percentiles(times),
                "status_counts": {str(c): codes.count(c) for c in set(codes)},
            }
            print(f"[phase8.5] concurrency={level:>3}  wall={wall_sec:6.2f}s  "
                  f"throughput={out[level]['throughput_req_per_sec']}/s  "
                  f"p50={out[level]['latency_ms']['p50']}ms  statuses={out[level]['status_counts']}")
            time.sleep(3)  # let the rate-limit window breathe between levels
    return {"name": "concurrency_http_after_fix", "by_level": out}


def run_all() -> dict:
    print("[phase8.5] /health/detailed latency after fix...")
    results = {"health_detailed_after": bench_health_detailed()}
    print("[phase8.5] waiting 65s for a clean 120/min rate-limit window before the concurrency test...")
    time.sleep(65)
    print("[phase8.5] concurrency after fix (HTTP, same levels as Phase 7's http_sanity)...")
    results["concurrency_after"] = bench_concurrency_http()

    out_path = RESULTS_DIR / "phase8_5_reprofile.json"
    out_path.write_text(json.dumps(results, indent=2, default=str), encoding="utf-8")
    print(f"[phase8.5] written -> {out_path}")
    return results


if __name__ == "__main__":
    run_all()
